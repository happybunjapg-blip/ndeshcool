"""QR Code generation and deep link parsing for WaterPilot invitations.

Provides:
- generate_invitation_qr(invitation) -> PIL Image containing QR with deep link URL
- generate_invitation_qr_base64(invitation) -> base64 PNG string
- parse_deep_link(url) -> dict | None (decoded invitation payload from URL)

The QR payload is a deep link URL:
  waterpilot://join?code=483921&type=worker&business_id=uuid...

Android Camera recognizes the QR → launches WaterPilot → URL is parsed.
"""
from typing import Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import qrcode
from PIL import Image
import io
import base64


DEEP_LINK_SCHEME = "waterpilot"
DEEP_LINK_HOST = "join"


class QRDecodeError(Exception):
    pass


def _build_deep_link(code: str, invitation_type: str, business_id: str) -> str:
    """Build a deep link URL for the invitation.
    
    Format: waterpilot://join?code=XXX&type=worker&business_id=UUID
    """
    params = urlencode({
        "code": code,
        "type": invitation_type,
        "business_id": business_id,
    })
    url = urlunparse((DEEP_LINK_SCHEME, DEEP_LINK_HOST, "", "", params, ""))
    print(f"[QR_DEBUG] _build_deep_link: code={code!r}, invitation_type={invitation_type!r}, business_id={business_id!r}")
    print(f"[QR_DEBUG] _build_deep_link: final URL={url!r}")
    return url


def generate_invitation_qr(code: str, invitation_type: str, business_id: str) -> Image.Image:
    """Generate a QR code image containing a deep link URL.
    
    Args:
        code: The 6-digit invitation code.
        invitation_type: "worker" or "owner".
        business_id: The UUID of the business.
    
    Returns:
        PIL Image of the QR code.
    """
    deep_link = _build_deep_link(code, invitation_type, business_id)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(deep_link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img


def generate_invitation_qr_base64(code: str, invitation_type: str, business_id: str) -> str:
    """Generate QR code and return as a base64-encoded PNG string."""
    img = generate_invitation_qr(code, invitation_type, business_id)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def parse_deep_link(url: str) -> Optional[dict]:
    """Parse a deep link URL into an invitation payload dict.
    
    Accepts multiple formats:
      - Full URL:   waterpilot://join?code=XXX&type=worker&business_id=UUID
      - Route path: /join?code=XXX&type=worker&business_id=UUID
      - Query only: join?code=XXX&type=worker&business_id=UUID
      - Bare query: ?code=XXX&type=worker&business_id=UUID
    
    Returns:
        dict with keys: code, type, business_id, or None if invalid.
    """
    if not url:
        print(f"[PARSE_DEBUG] parse_deep_link: url is empty, returning None")
        return None
    
    # Strip leading / for scheme detection
    url = url.strip()
    print(f"[PARSE_DEBUG] parse_deep_link: raw URL={url!r}")
    
    try:
        parsed = urlparse(url)
        print(f"[PARSE_DEBUG] urlparse result: scheme={parsed.scheme!r}, hostname={parsed.hostname!r}, path={parsed.path!r}, query={parsed.query!r}")
    except Exception as exc:
        print(f"[PARSE_DEBUG] urlparse exception: {exc}")
        return None
    
    # Check if this is a full waterpilot://join URL
    if parsed.scheme == DEEP_LINK_SCHEME:
        if parsed.hostname != DEEP_LINK_HOST:
            print(f"[PARSE_DEBUG] scheme=waterpilot but hostname={parsed.hostname!r} != 'join', returning None")
            return None
        print(f"[PARSE_DEBUG] scheme=waterpilot, hostname=join -> valid deep link format")
    else:
        # For route-format URLs (/join?code=... or join?code=...),
        # check that the path contains 'join'
        path = parsed.path or ""
        if not path.endswith("join") and path not in ("", "/"):
            print(f"[PARSE_DEBUG] path={path!r} does not contain 'join', returning None")
            return None
        print(f"[PARSE_DEBUG] non-waterpilot scheme, path={path!r} -> treating as route format")
    
    params = parse_qs(parsed.query, keep_blank_values=False)
    print(f"[PARSE_DEBUG] parsed query params: {params}")
    
    code = (params.get("code", [""])[0]).strip()
    inv_type = (params.get("type", [""])[0]).strip().lower()
    business_id = (params.get("business_id", [""])[0]).strip()
    
    print(f"[PARSE_DEBUG] extracted: code={code!r}, type={inv_type!r}, business_id={business_id!r}")
    
    if not code or inv_type not in ("worker", "owner") or not business_id:
        print(f"[PARSE_DEBUG] validation failed: code={code!r}, type={inv_type!r}, business_id={business_id!r}")
        return None
    
    result = {
        "code": code,
        "type": inv_type,
        "business_id": business_id,
    }
    print(f"[PARSE_DEBUG] returning: {result}")
    return result


# Keep decode_qr_data as an alias for backward compatibility
# (it will also accept JSON payloads for transition period)
def decode_qr_data(data: str) -> Optional[dict]:
    """Decode QR string data. Accepts both deep link URLs and JSON payloads.
    
    First tries deep link parsing, falls back to JSON parsing.
    
    Returns:
        dict with parsed fields, or None if invalid.
    """
    if not data:
        return None
    
    # Try deep link parsing first
    result = parse_deep_link(data.strip())
    if result is not None:
        return result
    
    # Fallback: try JSON parsing (for backward compatibility)
    import json
    try:
        payload = json.loads(data.strip())
    except (json.JSONDecodeError, ValueError):
        return None
    
    code = payload.get("code", "").strip()
    inv_type = payload.get("type", "").strip().lower()
    business_id = payload.get("business_id", "").strip()
    
    if not code or inv_type not in ("worker", "owner") or not business_id:
        return None
    
    return {
        "code": code,
        "type": inv_type,
        "business_id": business_id,
    }