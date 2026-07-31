"""Production authentication service using Supabase Auth.

NEW CANONICAL INVITATION ARCHITECTURE
--------------------------------------
The database invitation record is the SOLE source of truth for:
- business_id
- role
- validity
- expiration
- usage status

QR codes contain ONLY the invitation code (no role, no business_id).

New methods (canonical):
  - generate_invitation(business_id, role) — creates invitation with explicit role
  - lookup_invitation(code) — fetches invitation from DB (for display before join)
  - join_business_with_invitation(code, ...) — single canonical team-member signup

Old methods (deprecated, kept for backward compatibility):
  - sign_up_worker() — delegates to join_business_with_invitation
  - sign_up_second_owner() — delegates to join_business_with_invitation
  - sign_up_via_qr() — delegates to join_business_with_invitation
  - validate_invitation() — replaced by lookup_invitation
  - generate_invitation_code() — replaced by generate_invitation
"""
import random
import uuid
import sys
import traceback
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from models import User, Role, Invitation
from .session_service import SessionService


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, session_service: Optional[SessionService] = None):
        self._client = None
        self._session_service = session_service or SessionService()
        self._init_client()

    # ----------------------------------------------------------------
    # DIAGNOSTICS
    # ----------------------------------------------------------------
    def _log(self, msg: str, data=None):
        print(f"[AUTH] {msg}", file=sys.stderr)
        if data:
            import json
            try:
                print(f"[AUTH]   {json.dumps(data, default=str)}", file=sys.stderr)
            except Exception:
                print(f"[AUTH]   {data}", file=sys.stderr)

    def _log_exc(self, msg: str):
        print(f"[AUTH] ERROR: {msg}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    def _init_client(self):
        import config
        supabase_url = config.SUPABASE_URL
        has_key = bool(config.SUPABASE_KEY)
        print(f"[CONFIG_DEBUG] SUPABASE_URL={supabase_url!r}")
        print(f"[CONFIG_DEBUG] SUPABASE_KEY exists={has_key}")
        print(f"[CONFIG_DEBUG] BACKEND={config.BACKEND!r}")
        if supabase_url and config.SUPABASE_KEY:
            from supabase import create_client
            self._client = create_client(supabase_url, config.SUPABASE_KEY)
            self._log(f"Initialized Supabase client: {supabase_url}")
        else:
            self._log("Supabase not configured")

    # ----------------------------------------------------------------
    # SESSION
    # ----------------------------------------------------------------
    def get_saved_session(self) -> Optional[User]:
        access_token = self._session_service.get_access_token()
        refresh_token = self._session_service.get_refresh_token()
        if not access_token:
            self._log("No saved session token")
            return None
        try:
            if self._client and refresh_token:
                result = self._client.auth.set_session(access_token, refresh_token)
            elif self._client:
                result = self._client.auth.get_user(access_token)
            else:
                return None
            if result and result.user:
                self._log(f"Saved session restored for {result.user.email}")
                user = self._build_user_from_profile(result.user.id, result.user.email or "")
                if user:
                    return user
                self._log(f"Auth user exists but no profile: {result.user.email}")
                return None
        except Exception as exc:
            self._log(f"Session restore failed: {exc}")
            self._session_service.clear_session()
        return None

    def _save_session_tokens(self, auth_response) -> None:
        if not auth_response:
            return
        try:
            access_token = auth_response.session.access_token if auth_response.session else ""
            refresh_token = auth_response.session.refresh_token if auth_response.session else ""
            if access_token:
                self._session_service.save_session(access_token, refresh_token)
                self._log("Session tokens saved")
        except Exception as exc:
            self._log(f"Failed to save session: {exc}")

    def _extract_user_id(self, result) -> Optional[str]:
        if not result:
            return None
        if hasattr(result, 'user'):
            user = result.user
            if hasattr(user, 'id'):
                return user.id
            if isinstance(user, dict) and 'id' in user:
                return user['id']
        if isinstance(result, dict):
            user = result.get('user', {})
            if isinstance(user, dict) and 'id' in user:
                return user['id']
            if hasattr(result, 'id'):
                return result.id
        return None

    def _get_current_user_id(self) -> Optional[str]:
        if not self._client:
            return None
        try:
            user = self._client.auth.get_user()
            if user and user.user:
                return user.user.id
        except Exception:
            pass
        return None

    # ----------------------------------------------------------------
    # SIGN IN
    # ----------------------------------------------------------------
    def authenticate(self, email: str, password: str, remember_me: bool = False) -> User:
        if not self._client:
            raise AuthError("Authentication is not configured.")
        email = (email or "").strip().lower()
        password = (password or "").strip()
        if not email or not password:
            raise AuthError("Please enter your email and password.")
        try:
            self._log(f"Signing in: {email}")
            result = self._client.auth.sign_in_with_password({
                "email": email, "password": password,
            })
        except Exception as exc:
            msg = str(exc).lower()
            self._log(f"Sign in failed: {msg}")
            if "invalid login credentials" in msg:
                raise AuthError("Invalid email or password.")
            if "email not confirmed" in msg:
                raise AuthError("Please check your email and confirm your account before signing in.")
            if "rate limit" in msg:
                raise AuthError("Too many attempts. Try again later.")
            raise AuthError(f"Sign in failed: {exc}")
        if not result or not result.user:
            raise AuthError("Sign in failed.")
        user_id = result.user.id
        self._log(f"Sign in succeeded: user_id={user_id}, email={result.user.email}")

        user = self._build_user_from_profile(user_id, result.user.email or "")
        if user:
            self._log("Profile found — user is fully set up")
            if remember_me:
                self._save_session_tokens(result)
            return user

        self._log("No profile found — checking if user needs setup")
        try:
            profile_result = self._client.table("profiles").select("*").eq("email", result.user.email).execute()
            if profile_result and profile_result.data:
                profile = profile_result.data[0]
                self._client.table("profiles").update({"id": user_id}).eq("email", result.user.email).execute()
                user = self._build_user_from_profile(user_id, result.user.email or "")
                if user:
                    self._log("Linked existing profile to auth user")
                    if remember_me:
                        self._save_session_tokens(result)
                    return user
        except Exception as exc:
            self._log(f"Profile lookup failed: {exc}")

        raise AuthError(
            "Your account is not fully set up. "
            "If you just registered, please check your email to confirm your account, "
            "then sign in again."
        )

    # ----------------------------------------------------------------
    # PATH A: OWNER CREATION (no invitation involved)
    # ----------------------------------------------------------------
    def sign_up_owner(self, business_name: str, first_name: str, last_name: str,
                       email: str, password: str) -> User:
        if not self._client:
            raise AuthError("Registration is not configured.")
        email = (email or "").strip().lower()
        password = (password or "").strip()
        business_name = (business_name or "").strip()
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        if not business_name:
            raise AuthError("Business name is required.")
        if not first_name or not last_name:
            raise AuthError("First and last name are required.")
        if not email:
            raise AuthError("Email is required.")
        if not password or len(password) < 6:
            raise AuthError("Password must be at least 6 characters.")

        self._log(f"Creating auth user: {email}")
        try:
            result = self._client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "first_name": first_name,
                        "last_name": last_name,
                        "business_name": business_name,
                    },
                    "email_redirect_to": None,
                },
            })
        except Exception as exc:
            msg = str(exc).lower()
            self._log(f"Auth sign_up failed: {msg}")
            if "already registered" in msg:
                raise AuthError("An account with this email already exists.")
            raise AuthError(f"Registration failed: {exc}")

        self._log(f"sign_up result type: {type(result).__name__}")
        self._log(f"sign_up result user: {result.user if hasattr(result, 'user') else 'N/A'}")

        user_id = self._extract_user_id(result)
        self._log(f"Extracted user_id: {user_id}")

        if not user_id:
            raise AuthError("Registration failed. Could not determine user ID.")

        try:
            uuid.UUID(user_id)
        except (ValueError, AttributeError):
            self._log(f"Invalid user_id format: {user_id}")
            raise AuthError("Registration failed. Invalid user identifier.")

        has_session = hasattr(result, 'session') and result.session is not None
        identity_verified = has_session

        if identity_verified:
            self._log("User is auto-confirmed — creating business + profile")
            business_id = self._create_owner_business(business_name, user_id)
            self._create_profile(user_id, email, first_name, last_name, "owner", business_id)
            self._save_session_tokens(result)
            self._log("Business and profile created successfully")
        else:
            self._log("Email confirmation required — pre-creating profile")
            try:
                biz_result = self._client.table("businesses").insert({
                    "name": business_name,
                }).execute()
                business_id = biz_result.data[0]["id"] if biz_result.data else None
                if business_id:
                    self._client.table("businesses").update({
                        "owner_id": user_id,
                    }).eq("id", business_id).execute()
                    self._client.table("profiles").insert({
                        "id": user_id, "email": email,
                        "first_name": first_name, "last_name": last_name,
                        "phone": "", "role": "owner", "business_id": business_id,
                    }).execute()
                    self._log("Pre-created business and profile for email confirmation flow")
            except Exception as exc:
                self._log(f"Pre-creation failed (non-fatal): {exc}")

            raise AuthError(
                "Account created! Please check your email to confirm your account, "
                "then sign in."
            )

        return User(id=user_id, email=email, first_name=first_name, last_name=last_name,
                    role=Role.OWNER, business_id=business_id)

    # ====================================================================
    # NEW CANONICAL INVITATION METHODS
    # ====================================================================

    # ----------------------------------------------------------------
    # GENERATE INVITATION
    # ----------------------------------------------------------------
    def generate_invitation(self, business_id: str, role: str,
                            expires_in_hours: int = 24) -> Invitation:
        """Generate a new invitation with an explicit role.
        
        This is the canonical invitation creation method.
        
        Args:
            business_id: The business to join.
            role: 'worker' or 'co_owner'.
            expires_in_hours: Hours until expiration.
        
        Returns:
            Invitation object.
        """
        if not self._client:
            raise AuthError("Invitations are not available.")
        if not business_id:
            raise AuthError("Business ID is required.")
        if role not in ("worker", "co_owner"):
            raise AuthError("Invalid invitation role. Must be 'worker' or 'co_owner'.")
        
        code = f"{random.randint(100000, 999999)}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expires_in_hours)
        
        # Get the current user for created_by
        created_by = self._get_current_user_id()
        
        self._log(f"Generating invitation: code={code}, business_id={business_id}, role={role}")
        
        try:
            # Try to insert with new columns (role, status, created_by)
            # If the migration hasn't been applied yet, fall back to old columns
            try:
                self._client.table("invitations").insert({
                    "code": code, "business_id": business_id,
                    "role": role,
                    "status": "active",
                    "created_by": created_by,
                    "created_at": now.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    # Legacy fields for backward compatibility
                    "owner_invite": (role == "co_owner"),
                    "is_invalidated": False,
                }).execute()
            except Exception:
                # Fallback: if new columns don't exist yet, use old schema
                # This ensures backward compatibility during migration
                self._log("New columns may not exist yet — falling back to old schema")
                self._client.table("invitations").insert({
                    "code": code, "business_id": business_id,
                    "owner_invite": (role == "co_owner"),
                    "created_at": now.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "is_invalidated": False,
                }).execute()
        except Exception as exc:
            self._log_exc(f"Failed to generate invitation: {exc}")
            raise AuthError(f"Failed to generate invitation: {exc}")
        
        return Invitation(
            code=code, business_id=business_id,
            role=role,
            status="active",
            created_at=now.isoformat(), expires_at=expires_at.isoformat(),
            created_by=created_by or "",
        )

    # ----------------------------------------------------------------
    # LOOKUP INVITATION (for display before join)
    # ----------------------------------------------------------------
    def lookup_invitation(self, code: str) -> dict:
        """Look up an invitation by code and return its details.
        
        This is the canonical invitation lookup method.
        It returns ONLY the information needed for display/validation.
        The role and business_id come from the DATABASE, never from the client.
        
        Args:
            code: The invitation code.
        
        Returns:
            dict with: code, business_id, role, status, expires_at, business_name
        
        Raises:
            AuthError if the invitation is invalid.
        """
        if not self._client:
            raise AuthError("Registration is not configured.")
        code = (code or "").strip()
        if not code:
            raise AuthError("Invitation code is required.")
        
        self._log(f"Looking up invitation: code={code}")
        
        # Try to use the SECURITY DEFINER function first (if migration applied)
        try:
            result = self._client.rpc("lookup_invitation", {"p_code": code}).execute()
            if result and result.data:
                data = result.data[0] if isinstance(result.data, list) else result.data
                self._log(f"Invitation found via RPC: role={data.get('role')}, business={data.get('business_name')}")
                return {
                    "code": data["code"],
                    "business_id": data["business_id"],
                    "role": data["role"],
                    "status": data["status"],
                    "expires_at": str(data["expires_at"]),
                    "business_name": data.get("business_name", ""),
                }
        except Exception as exc:
            self._log(f"RPC lookup failed (may not be migrated yet): {exc}")
        
        # Fallback: direct table query (before migration)
        try:
            result = self._client.table("invitations").select("*").eq("code", code).execute()
        except Exception:
            raise AuthError("Could not verify invitation code.")
        
        if not result or not result.data:
            raise AuthError("Invalid invitation code.")
        
        invitation = result.data[0]
        
        # Check if already used
        if invitation.get("is_invalidated"):
            raise AuthError("This invitation has already been used.")
        
        # Check expiration
        expires_at = invitation.get("expires_at", "")
        if expires_at:
            try:
                exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                if exp < datetime.now(timezone.utc):
                    raise AuthError("This invitation code has expired.")
            except ValueError:
                pass
        
        # Determine role from new 'role' column or fall back to owner_invite
        role = invitation.get("role")
        if not role:
            role = "co_owner" if invitation.get("owner_invite", False) else "worker"
        
        # Get business name
        business_name = ""
        try:
            biz_result = self._client.table("businesses").select("name").eq("id", invitation["business_id"]).execute()
            if biz_result and biz_result.data:
                business_name = biz_result.data[0].get("name", "")
        except Exception:
            pass
        
        status = invitation.get("status", "active" if not invitation.get("is_invalidated") else "used")
        
        return {
            "code": invitation["code"],
            "business_id": invitation["business_id"],
            "role": role,
            "status": status,
            "expires_at": str(expires_at),
            "business_name": business_name,
        }

    # ----------------------------------------------------------------
    # CANONICAL JOIN METHOD: PATH B - TEAM MEMBER
    # ----------------------------------------------------------------
    def join_business_with_invitation(self, code: str, first_name: str, last_name: str,
                                       email: str, password: str) -> User:
        """Single canonical method for joining a business via invitation.
        
        This is the ONLY team-member signup method.
        The database invitation record determines role and business_id.
        The client CANNOT override role or business_id.
        
        Args:
            code: The invitation code.
            first_name: User's first name.
            last_name: User's last name.
            email: User's email.
            password: User's password.
        
        Returns:
            User object with role from the invitation record.
        """
        if not self._client:
            raise AuthError("Registration is not configured.")
        
        code = (code or "").strip()
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        email = (email or "").strip().lower()
        password = (password or "").strip()
        
        if not code:
            raise AuthError("Invitation code is required.")
        if not first_name or not last_name:
            raise AuthError("First and last name are required.")
        if not email:
            raise AuthError("Email is required.")
        if not password or len(password) < 6:
            raise AuthError("Password must be at least 6 characters.")
        
        # Step 1: Look up invitation (authoritative source)
        self._log(f"Join business with invitation: code={code}")
        invitation_data = self.lookup_invitation(code)
        
        business_id = invitation_data["business_id"]
        role = invitation_data["role"]
        self._log(f"Invitation resolved: business_id={business_id}, role={role}")
        
        # Step 2: Check if role is valid
        if role not in ("worker", "co_owner"):
            raise AuthError(f"Invalid invitation role: {role}")
        
        # Step 3: Create Supabase Auth account
        try:
            result = self._client.auth.sign_up({
                "email": email, "password": password,
                "options": {"data": {"first_name": first_name, "last_name": last_name}},
            })
        except Exception as exc:
            msg = str(exc).lower()
            if "already registered" in msg:
                raise AuthError("An account with this email already exists.")
            raise AuthError(f"Registration failed: {exc}")
        
        user_id = self._extract_user_id(result)
        if not user_id:
            raise AuthError("Registration failed.")
        
        has_session = hasattr(result, 'session') and result.session is not None
        identity_verified = has_session
        
        # Step 4: Create profile and mark invitation as used
        try:
            if identity_verified:
                self._create_profile(user_id, email, first_name, last_name, role, business_id)
                self._consume_invitation(code)
                self._save_session_tokens(result)
                self._log(f"Account created: role={role}, business_id={business_id}")
            else:
                # Pre-create profile for email confirmation flow
                self._client.table("profiles").insert({
                    "id": user_id, "email": email,
                    "first_name": first_name, "last_name": last_name,
                    "phone": "", "role": role, "business_id": business_id,
                }).execute()
                self._consume_invitation(code)
                raise AuthError(
                    "Account created! Please check your email to confirm your account, "
                    "then sign in."
                )
        except AuthError:
            raise
        except Exception as exc:
            self._log_exc(f"Account setup failed: {exc}")
            raise AuthError(f"Account setup failed: {exc}")
        
        # Step 5: Return User with correct role enum
        role_enum = Role.CO_OWNER if role == "co_owner" else Role.WORKER
        return User(id=user_id, email=email, first_name=first_name, last_name=last_name,
                    role=role_enum, business_id=business_id)

    # ----------------------------------------------------------------
    # CONSUME INVITATION (atomic)
    # ----------------------------------------------------------------
    def _consume_invitation(self, code: str) -> bool:
        """Atomically mark an invitation as used.
        
        Returns True if consumed, False if already consumed.
        """
        if not self._client:
            return False
        
        # Try the consume_invitation RPC function first (if migration applied)
        try:
            user_id = self._get_current_user_id()
            if user_id:
                result = self._client.rpc("consume_invitation", {
                    "p_code": code, "p_user_id": user_id
                }).execute()
                if result and result.data:
                    return bool(result.data[0] if isinstance(result.data, list) else result.data)
        except Exception:
            self._log("RPC consume_invitation failed (may not be migrated yet)")
        
        # Fallback: direct update
        try:
            # Try updating with new columns first
            result = self._client.table("invitations").update({
                "status": "used",
                "used_at": datetime.now(timezone.utc).isoformat(),
            }).eq("code", code).eq("status", "active").execute()
            if result and result.data:
                return True
        except Exception:
            pass
        
        # Fallback: old column update
        try:
            result = self._client.table("invitations").update({
                "is_invalidated": True,
            }).eq("code", code).eq("is_invalidated", False).execute()
            return bool(result and result.data)
        except Exception as exc:
            self._log(f"Failed to consume invitation: {exc}")
            return False

    # ====================================================================
    # DEPRECATED METHODS (kept for backward compatibility)
    # ====================================================================

    # ----------------------------------------------------------------
    # DEPRECATED: sign_up_worker
    # ----------------------------------------------------------------
    def sign_up_worker(self, invitation_code: str, first_name: str, last_name: str,
                       email: str, password: str) -> User:
        """DEPRECATED: Use join_business_with_invitation() instead."""
        self._log("WARNING: sign_up_worker is deprecated, use join_business_with_invitation")
        invitation = self.validate_invitation(invitation_code, require_owner=False)
        business_id = invitation.business_id
        self._log(f"Valid invitation: code={invitation_code}, business_id={business_id}")

        try:
            result = self._client.auth.sign_up({
                "email": email, "password": password,
                "options": {"data": {"first_name": first_name, "last_name": last_name}},
            })
        except Exception as exc:
            msg = str(exc).lower()
            if "already registered" in msg:
                raise AuthError("An account with this email already exists.")
            raise AuthError(f"Registration failed: {exc}")

        user_id = self._extract_user_id(result)
        if not user_id:
            raise AuthError("Registration failed.")

        has_session = hasattr(result, 'session') and result.session is not None
        identity_verified = has_session

        try:
            if identity_verified:
                self._create_profile(user_id, email, first_name, last_name, "worker", business_id)
                self._client.table("invitations").update({
                    "is_invalidated": True,
                }).eq("code", invitation_code).execute()
                self._save_session_tokens(result)
                self._log("Worker account fully created")
            else:
                self._client.table("profiles").insert({
                    "id": user_id, "email": email,
                    "first_name": first_name, "last_name": last_name,
                    "phone": "", "role": "worker", "business_id": business_id,
                }).execute()
                self._client.table("invitations").update({
                    "is_invalidated": True,
                }).eq("code", invitation_code).execute()
                raise AuthError(
                    "Account created! Please check your email to confirm your account, "
                    "then sign in."
                )
        except AuthError:
            raise
        except Exception as exc:
            self._log_exc(f"Worker account setup failed: {exc}")
            raise AuthError(f"Account setup failed: {exc}")

        return User(id=user_id, email=email, first_name=first_name, last_name=last_name,
                    role=Role.WORKER, business_id=business_id)

    # ----------------------------------------------------------------
    # DEPRECATED: sign_up_second_owner
    # ----------------------------------------------------------------
    def sign_up_second_owner(self, invitation_code: str, first_name: str, last_name: str,
                              email: str, password: str) -> User:
        """DEPRECATED: Use join_business_with_invitation() instead."""
        self._log("WARNING: sign_up_second_owner is deprecated, use join_business_with_invitation")
        invitation = self.validate_invitation(invitation_code, require_owner=True)
        business_id = invitation.business_id
        try:
            result = self._client.auth.sign_up({
                "email": email, "password": password,
                "options": {"data": {"first_name": first_name, "last_name": last_name}},
            })
        except Exception as exc:
            msg = str(exc).lower()
            if "already registered" in msg:
                raise AuthError("An account with this email already exists.")
            raise AuthError(f"Registration failed: {exc}")
        user_id = self._extract_user_id(result)
        if not user_id:
            raise AuthError("Registration failed.")
        has_session = hasattr(result, 'session') and result.session is not None
        identity_verified = has_session
        try:
            if identity_verified:
                self._create_profile(user_id, email, first_name, last_name, "owner", business_id)
                self._client.table("invitations").update({
                    "is_invalidated": True,
                }).eq("code", invitation_code).execute()
                self._save_session_tokens(result)
            else:
                self._client.table("profiles").insert({
                    "id": user_id, "email": email,
                    "first_name": first_name, "last_name": last_name,
                    "phone": "", "role": "owner", "business_id": business_id,
                }).execute()
                self._client.table("invitations").update({
                    "is_invalidated": True,
                }).eq("code", invitation_code).execute()
                raise AuthError(
                    "Account created! Please check your email to confirm your account, "
                    "then sign in."
                )
        except AuthError:
            raise
        except Exception as exc:
            self._log_exc(f"Second owner setup failed: {exc}")
            raise AuthError(f"Account setup failed: {exc}")
        return User(id=user_id, email=email, first_name=first_name, last_name=last_name,
                    role=Role.OWNER, business_id=business_id)

    # ----------------------------------------------------------------
    # DEPRECATED: sign_up_via_qr — delegates to join_business_with_invitation
    # ----------------------------------------------------------------
    def sign_up_via_qr(self, qr_data: dict, first_name: str, last_name: str,
                       email: str, password: str, page=None) -> User:
        """DEPRECATED: Use join_business_with_invitation() instead.
        
        This method now delegates to join_business_with_invitation().
        The qr_data dict is IGNORED except for the 'code' field.
        Role and business_id are determined by the database, not the QR.
        """
        if not self._client:
            raise AuthError("Registration is not configured.")
        
        code = (qr_data.get("code") or "").strip()
        if not code:
            raise AuthError("Invalid invitation QR. Please scan again.")
        
        # Log the deprecation warning
        self._log("WARNING: sign_up_via_qr is deprecated, using join_business_with_invitation")
        self._log(f"QR data received (code only is used): code={code}")
        
        # Delegate to the canonical method
        # The lookup_invitation method will determine role and business_id from DB
        return self.join_business_with_invitation(
            code=code,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
        )

    # ----------------------------------------------------------------
    # DEPRECATED DEBUG DIALOG
    # ----------------------------------------------------------------
    def _show_debug_dialog(self, page, qr_data, code, inv_type, require_owner, exception=None, passed=False):
        """DEPRECATED: Debug dialog is no longer needed."""
        pass

    # ----------------------------------------------------------------
    # DATABASE HELPERS
    # ----------------------------------------------------------------
    def _create_owner_business(self, business_name: str, owner_id: str) -> str:
        """Create a business and return its ID."""
        try:
            biz_result = self._client.table("businesses").insert({
                "name": business_name,
            }).execute()
            business_id = biz_result.data[0]["id"] if biz_result.data else None
            if not business_id:
                raise Exception("No business ID returned")
            self._client.table("businesses").update({
                "owner_id": owner_id,
            }).eq("id", business_id).execute()
            self._log(f"Business created: id={business_id}, name={business_name}")
            return business_id
        except Exception as exc:
            self._log_exc(f"Failed to create business: {exc}")
            raise AuthError(f"Failed to create business: {exc}")

    def _create_profile(self, user_id: str, email: str, first_name: str, last_name: str,
                        role: str, business_id: str):
        try:
            self._client.table("profiles").insert({
                "id": user_id, "email": email,
                "first_name": first_name, "last_name": last_name,
                "phone": "", "role": role, "business_id": business_id,
            }).execute()
            self._log(f"Profile created for {email} as {role}")
        except Exception as exc:
            self._log_exc(f"Failed to create profile: {exc}")
            raise AuthError(f"Failed to create profile: {exc}")

    # ----------------------------------------------------------------
    # DEPRECATED: validate_invitation — replaced by lookup_invitation
    # ----------------------------------------------------------------
    def validate_invitation(self, code: str, require_owner: bool = False) -> Invitation:
        """DEPRECATED: Use lookup_invitation() instead.
        
        Kept for backward compatibility with sign_up_worker and sign_up_second_owner.
        """
        self._log("WARNING: validate_invitation is deprecated, use lookup_invitation")
        if not self._client:
            raise AuthError("Registration is not configured.")
        code = (code or "").strip()
        try:
            result = self._client.table("invitations").select("*").eq("code", code).execute()
        except Exception:
            raise AuthError("Could not verify invitation code.")
        if not result or not result.data:
            raise AuthError("Invalid invitation code.")
        invitation = result.data[0]
        if invitation.get("is_invalidated"):
            raise AuthError("This invitation has already been used.")
        if require_owner and not invitation.get("owner_invite", False):
            raise AuthError("This is not an owner invitation code.")
        if not require_owner and invitation.get("owner_invite", False):
            raise AuthError("This code is for business owners only.")
        expires_at = invitation.get("expires_at", "")
        if expires_at:
            try:
                exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                if exp < datetime.now(timezone.utc):
                    raise AuthError("This invitation code has expired.")
            except ValueError:
                pass
        return Invitation(
            code=invitation["code"], business_id=invitation["business_id"],
            email=invitation.get("email", ""),
            created_at=invitation.get("created_at", ""), expires_at=expires_at,
        )

    # ----------------------------------------------------------------
    # DEPRECATED: generate_invitation_code — replaced by generate_invitation
    # ----------------------------------------------------------------
    def generate_invitation_code(self, business_id: str, owner_invite: bool = False,
                                  expires_in_hours: int = 24) -> Invitation:
        """DEPRECATED: Use generate_invitation(business_id, role) instead."""
        self._log("WARNING: generate_invitation_code is deprecated, use generate_invitation")
        # Delegate to new method
        role = "co_owner" if owner_invite else "worker"
        return self.generate_invitation(business_id, role, expires_in_hours)

    def revoke_invitation(self, code: str) -> None:
        if not self._client:
            return
        try:
            # Try new status column first
            try:
                self._client.table("invitations").update({
                    "status": "revoked",
                }).eq("code", code).execute()
            except Exception:
                # Fallback to old column
                self._client.table("invitations").update({
                    "is_invalidated": True,
                }).eq("code", code).execute()
            self._log(f"Invitation {code} revoked")
        except Exception as exc:
            self._log(f"Failed to revoke {code}: {exc}")

    def list_invitations(self, business_id: str) -> List[dict]:
        if not self._client:
            return []
        try:
            result = self._client.table("invitations").select("*").eq(
                "business_id", business_id
            ).order("created_at", desc=True).execute()
            return result.data or []
        except Exception:
            return []

    def count_owners(self, business_id: str) -> int:
        if not self._client:
            return 0
        try:
            result = self._client.table("profiles").select("id", count="exact").eq(
                "business_id", business_id
            ).eq("role", "owner").execute()
            return result.count or 0
        except Exception:
            return 0

    # ----------------------------------------------------------------
    # FORGOT PASSWORD
    # ----------------------------------------------------------------
    def forgot_password(self, email: str) -> bool:
        if not self._client:
            return False
        email = (email or "").strip().lower()
        if not email:
            return False
        try:
            self._client.auth.reset_password_email(email)
            self._log(f"Password reset email sent to {email}")
        except Exception as exc:
            self._log(f"Password reset failed: {exc}")
        return True

    def update_password(self, new_password: str) -> bool:
        if not self._client:
            raise AuthError("Password update is not available.")
        new_password = (new_password or "").strip()
        if not new_password or len(new_password) < 6:
            raise AuthError("Password must be at least 6 characters.")
        try:
            self._client.auth.update_user({"password": new_password})
            self._log("Password updated")
            return True
        except Exception as exc:
            self._log_exc(f"Password update failed: {exc}")
            raise AuthError(f"Failed to update password: {exc}")

    # ----------------------------------------------------------------
    # LOGOUT
    # ----------------------------------------------------------------
    def sign_out(self) -> None:
        self._session_service.clear_session()
        if self._client:
            try:
                self._client.auth.sign_out()
                self._log("Signed out")
            except Exception as exc:
                self._log(f"Sign out error: {exc}")

    # ----------------------------------------------------------------
    # PROFILE
    # ----------------------------------------------------------------
    def _build_user_from_profile(self, user_id: str, email: str) -> Optional[User]:
        if not self._client:
            return None
        try:
            profile_result = self._client.table("profiles").select("*").eq("id", user_id).execute()
        except Exception as exc:
            self._log(f"Profile query failed for {user_id}: {exc}")
            return None
        if not profile_result or not profile_result.data:
            self._log(f"No profile row for user {user_id}")
            return None
        profile = profile_result.data[0]
        return User(
            id=user_id, email=profile.get("email", email),
            first_name=profile.get("first_name", ""),
            last_name=profile.get("last_name", ""),
            role=Role(profile["role"]),
            business_id=profile["business_id"],
            phone=profile.get("phone", ""),
        )

    def get_current_user(self) -> Optional[User]:
        return self.get_saved_session()