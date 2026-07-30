"""Production authentication service using Supabase Auth.

All authentication uses Supabase Auth. No demo accounts exist.
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
        # SAFE DIAGNOSTIC: Log which Supabase URL is being used (NOT the key)
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
                # User exists in auth but no profile yet — they need to complete setup
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
        """Get the authenticated user's ID from the active session."""
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

        # Try to build user from profile
        user = self._build_user_from_profile(user_id, result.user.email or "")
        if user:
            self._log("Profile found — user is fully set up")
            if remember_me:
                self._save_session_tokens(result)
            return user

        # No profile yet — user signed up but hasn't completed setup
        # Try to find their profile or create it
        self._log("No profile found — checking if user needs setup")
        try:
            # Look for the user's email in pending setups
            profile_result = self._client.table("profiles").select("*").eq("email", result.user.email).execute()
            if profile_result and profile_result.data:
                profile = profile_result.data[0]
                # Found a profile by email — link it to this user
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
    # CREATE ACCOUNT
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

        # Step 1: Create auth user via Supabase
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
                    # Don't redirect — this is a desktop app
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

        # Validate UUID
        try:
            uuid.UUID(user_id)
        except (ValueError, AttributeError):
            self._log(f"Invalid user_id format: {user_id}")
            raise AuthError("Registration failed. Invalid user identifier.")

        # Step 2: Check if email confirmation is required
        has_session = hasattr(result, 'session') and result.session is not None
        identity_verified = has_session  # If we got a session, user is auto-confirmed

        if identity_verified:
            self._log("User is auto-confirmed (no email needed) — creating business + profile")
            business_id = self._create_owner_business(business_name, user_id)
            self._create_profile(user_id, email, first_name, last_name, "owner", business_id)
            self._save_session_tokens(result)
            self._log("Business and profile created successfully")
        else:
            self._log("Email confirmation required — pre-creating profile for later setup")
            # Pre-create the profile so it's ready when they confirm email and sign in
            try:
                # First create a business (we need a business_id)
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

    def sign_up_worker(self, invitation_code: str, first_name: str, last_name: str,
                       email: str, password: str) -> User:
        if not self._client:
            raise AuthError("Registration is not configured.")
        email = (email or "").strip().lower()
        password = (password or "").strip()
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        if not first_name or not last_name:
            raise AuthError("First and last name are required.")
        if not email:
            raise AuthError("Email is required.")
        if not password or len(password) < 6:
            raise AuthError("Password must be at least 6 characters.")

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
                # Pre-create profile for when they confirm email
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

    def sign_up_second_owner(self, invitation_code: str, first_name: str, last_name: str,
                              email: str, password: str) -> User:
        if not self._client:
            raise AuthError("Registration is not configured.")
        email = (email or "").strip().lower()
        password = (password or "").strip()
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        if not first_name or not last_name:
            raise AuthError("First and last name are required.")
        if not email:
            raise AuthError("Email is required.")
        if not password or len(password) < 6:
            raise AuthError("Password must be at least 6 characters.")
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
    # QR-BASED SIGNUP (WaterPilot redesign)
    # ----------------------------------------------------------------
    def sign_up_via_qr(self, qr_data: dict, first_name: str, last_name: str,
                       email: str, password: str, page=None) -> User:
        """Create account from decoded QR invitation payload.
        
        qr_data must contain:
          - code: the 6-digit invitation code
          - type: "worker" or "owner"
          - business_id: the business UUID
        
        The invitation is validated, then the user is created with the
        role determined by the QR type (not guessed).
        """
        if not self._client:
            raise AuthError("Registration is not configured.")
        
        code = (qr_data.get("code") or "").strip()
        inv_type = (qr_data.get("type") or "").strip().lower()
        business_id = (qr_data.get("business_id") or "").strip()
        
        if not code or inv_type not in ("worker", "owner") or not business_id:
            raise AuthError("Invalid invitation QR. Please scan again.")
        
        email = (email or "").strip().lower()
        password = (password or "").strip()
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        
        if not first_name or not last_name:
            raise AuthError("First and last name are required.")
        if not email:
            raise AuthError("Email is required.")
        if not password or len(password) < 6:
            raise AuthError("Password must be at least 6 characters.")
        
        print(f"[AUTH_DEBUG] sign_up_via_qr: received qr_data -> code={code!r}, inv_type={inv_type!r}, business_id={business_id!r}")
        require_owner = (inv_type == "owner")
        print(f"[AUTH_DEBUG] sign_up_via_qr: calling validate_invitation(code={code!r}, require_owner={require_owner!r})")
        # Validate the invitation code
        try:
            invitation = self.validate_invitation(code, require_owner=require_owner)
        except AuthError as exc:
            # Show debug dialog before re-raising
            self._show_debug_dialog(page, qr_data, code, inv_type, require_owner, exception=str(exc))
            raise
        
        if invitation.business_id != business_id:
            raise AuthError("Invitation does not match this business.")
        
        # Show debug dialog on validation success
        self._show_debug_dialog(page, qr_data, code, inv_type, require_owner, passed=True)
        
        self._log(f"QR signup: type={inv_type}, code={code}, business_id={business_id}")
        
        # Create the auth user
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
        
        role_str = "owner" if inv_type == "owner" else "worker"
        
        try:
            if identity_verified:
                self._create_profile(user_id, email, first_name, last_name, role_str, business_id)
                self._client.table("invitations").update({
                    "is_invalidated": True,
                }).eq("code", code).execute()
                self._save_session_tokens(result)
                self._log(f"{role_str.title()} account fully created via QR")
            else:
                # Pre-create profile for when they confirm email
                self._client.table("profiles").insert({
                    "id": user_id, "email": email,
                    "first_name": first_name, "last_name": last_name,
                    "phone": "", "role": role_str, "business_id": business_id,
                }).execute()
                self._client.table("invitations").update({
                    "is_invalidated": True,
                }).eq("code", code).execute()
                raise AuthError(
                    "Account created! Please check your email to confirm your account, "
                    "then sign in."
                )
        except AuthError:
            raise
        except Exception as exc:
            self._log_exc(f"QR account setup failed: {exc}")
            raise AuthError(f"Account setup failed: {exc}")
        
        role_enum = Role.OWNER if inv_type == "owner" else Role.WORKER
        return User(id=user_id, email=email, first_name=first_name, last_name=last_name,
                    role=role_enum, business_id=business_id)

    # ----------------------------------------------------------------
    # DEBUG DIALOG (temporary — shows runtime values on Android screen)
    # ----------------------------------------------------------------
    def _show_debug_dialog(self, page, qr_data, code, inv_type, require_owner, exception=None, passed=False):
        """Show an on-screen AlertDialog with debug values."""
        if page is None:
            print("[DEBUG_DIALOG] No page provided, skipping dialog")
            return
        
        try:
            # Get Supabase config info (safe - URL only, not the key)
            import config as app_config
            supabase_url = app_config.SUPABASE_URL
            backend = app_config.BACKEND
            
            # Fetch the DB record fresh for display
            db_code = "N/A"
            db_owner_invite = "N/A"
            db_business_id = "N/A"
            try:
                db_result = self._client.table("invitations").select("code, owner_invite, business_id").eq("code", code).execute()
                if db_result and db_result.data:
                    db_code = db_result.data[0].get("code", "N/A")
                    db_owner_invite = str(db_result.data[0].get("owner_invite", "N/A"))
                    db_business_id = db_result.data[0].get("business_id", "N/A")
            except Exception as exc:
                db_owner_invite = f"DB ERROR: {exc}"
            
            branch_info = exception if exception else "PASSED (no exception)"
            
            message = (
                f"CONFIG DEBUG\n\n"
                f"Supabase URL: {supabase_url}\n"
                f"Backend: {backend}\n\n"
                f"QR DEBUG\n\n"
                f"QR type: {inv_type}\n\n"
                f"Code: {code}\n\n"
                f"Require owner: {require_owner}\n\n"
                f"Database row:\n"
                f"  code: {db_code}\n"
                f"  owner_invite: {db_owner_invite}\n"
                f"  business_id: {db_business_id}\n\n"
                f"Branch executed: {branch_info}\n\n"
                f"Exception: {exception or 'None'}"
            )
            
            # Use page.run_task to show the dialog on the UI thread
            import asyncio
            async def _show():
                dialog = ft.AlertDialog(
                    title=ft.Text("QR DEBUG"),
                    content=ft.Text(message, size=12, selectable=True),
                    actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
                )
                page.open(dialog)
                page.update()
            
            # Run synchronously by scheduling on the page loop
            try:
                asyncio.run_coroutine_threadsafe(_show(), page.loop)
            except Exception:
                # Fallback: try direct call
                try:
                    dialog = ft.AlertDialog(
                        title=ft.Text("QR DEBUG"),
                        content=ft.Text(message, size=12, selectable=True),
                        actions=[ft.TextButton("OK", on_click=lambda e: page.close(dialog))],
                    )
                    page.open(dialog)
                    page.update()
                except Exception as exc2:
                    print(f"[DEBUG_DIALOG] Failed to show dialog: {exc2}")
        except Exception as exc:
            print(f"[DEBUG_DIALOG] Error: {exc}")

    # ----------------------------------------------------------------
    # DATABASE HELPERS
    # ----------------------------------------------------------------
    def _create_owner_business(self, business_name: str, owner_id: str) -> str:
        """Create a business and return its ID. owner_id is set after creation."""
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
    # INVITATION
    # ----------------------------------------------------------------
    def validate_invitation(self, code: str, require_owner: bool = False) -> Invitation:
        if not self._client:
            raise AuthError("Registration is not configured.")
        code = (code or "").strip()
        print(f"[AUTH_DEBUG] validate_invitation: code={code!r}, require_owner={require_owner!r}")
        try:
            result = self._client.table("invitations").select("*").eq("code", code).execute()
        except Exception:
            print(f"[AUTH_DEBUG] validate_invitation: DB query failed")
            raise AuthError("Could not verify invitation code.")
        if not result or not result.data:
            print(f"[AUTH_DEBUG] validate_invitation: no data returned for code={code!r}")
            raise AuthError("Invalid invitation code.")
        invitation = result.data[0]
        print(f"[AUTH_DEBUG] validate_invitation: DB record -> code={invitation.get('code')!r}, owner_invite={invitation.get('owner_invite')!r}, business_id={invitation.get('business_id')!r}")
        if invitation.get("is_invalidated"):
            print(f"[AUTH_DEBUG] validate_invitation: BRANCH 1 - is_invalidated=True, rejecting")
            raise AuthError("This invitation has already been used.")
        if require_owner and not invitation.get("owner_invite", False):
            print(f"[AUTH_DEBUG] validate_invitation: BRANCH 2 - require_owner=True but owner_invite=False, rejecting with 'not an owner invitation'")
            raise AuthError("This is not an owner invitation code.")
        if not require_owner and invitation.get("owner_invite", False):
            print(f"[AUTH_DEBUG] validate_invitation: BRANCH 3 - require_owner=False but owner_invite=True, rejecting with 'business owners only'")
            raise AuthError("This code is for business owners only.")
        print(f"[AUTH_DEBUG] validate_invitation: PASSED all checks")
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

    def generate_invitation_code(self, business_id: str, owner_invite: bool = False,
                                  expires_in_hours: int = 24) -> Invitation:
        if not self._client:
            raise AuthError("Invitations are not available.")
        code = f"{random.randint(100000, 999999)}"
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=expires_in_hours)
        print(f"[AUTH_DEBUG] generate_invitation_code called: business_id={business_id!r}, owner_invite={owner_invite!r}")
        print(f"[AUTH_DEBUG]   Generated code={code!r}, inserting into DB with owner_invite={owner_invite!r}")
        try:
            self._client.table("invitations").insert({
                "code": code, "business_id": business_id,
                "owner_invite": owner_invite,
                "created_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "is_invalidated": False,
            }).execute()
            print(f"[AUTH_DEBUG]   DB insert succeeded for code={code!r} with owner_invite={owner_invite!r}")
        except Exception as exc:
            print(f"[AUTH_DEBUG]   DB insert FAILED: {exc}")
            raise AuthError(f"Failed to generate invitation: {exc}")
        
        # VERIFY: Immediately SELECT back what was actually stored
        try:
            verify = self._client.table("invitations").select("code, owner_invite, business_id").eq("code", code).execute()
            if verify and verify.data:
                print(f"[AUTH_DEBUG]   VERIFY SELECT after INSERT: code={verify.data[0].get('code')!r}, owner_invite={verify.data[0].get('owner_invite')!r}, business_id={verify.data[0].get('business_id')!r}")
            else:
                print(f"[AUTH_DEBUG]   VERIFY SELECT returned no data for code={code!r}")
        except Exception as exc:
            print(f"[AUTH_DEBUG]   VERIFY SELECT FAILED: {exc}")
        
        return Invitation(code=code, business_id=business_id,
                          created_at=now.isoformat(), expires_at=expires_at.isoformat())

    def revoke_invitation(self, code: str) -> None:
        if not self._client:
            return
        try:
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