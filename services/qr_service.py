"""QR Code generation and deep link parsing for WaterPilot invitations.

The QR code contains ONLY the invitation code (no role, no business_id).
The database invitation record is the sole source of truth for:
- business_id
- role
- validity
- expiration

Target deep link format:
  waterpilot://join?code=123456
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


def _build_deep_link(code: str) -> str:
    """Build a deep link URL containing only the invitation code.
    
    Format: waterpilot://join?code=XXXXXX
    """
    params = urlencode({"code": code})
    url = urlunparse((DEEP_LINK_SCHEME, DEEP_LINK_HOST, "", "", params, ""))
    return url


def generate_invitation_qr(code: str) -> Image.Image:
    """Generate a QR code image containing a deep link URL with only the code.
    
    Args:
        code: The invitation code.
    
    Returns:
        PIL Image of the QR code.
    """
    deep_link = _build_deep_link(code)
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


def generate_invitation_qr_base64(code: str) -> str:
    """Generate QR code and return as a base64-encoded PNG string."""
    img = generate_invitation_qr(code)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def parse_deep_link(url: str) -> Optional[dict]:
    """Parse a deep link URL and extract ONLY the invitation code.
    
    Accepts multiple formats:
      - Full URL:   waterpilot://join?code=123456
      - Route path: /join?code=123456
      - Bare query: ?code=123456
    
    Returns:
        dict with key 'code' only, or None if invalid.
        Any extra parameters (type, business_id, etc.) are IGNORED.
    """
    if not url:
        return None

    url = url.strip()

    try:
        parsed = urlparse(url)
    except Exception:
        return None

    # Check if this is a full waterpilot://join URL
    if parsed.scheme == DEEP_LINK_SCHEME:
        if parsed.hostname != DEEP_LINK_HOST:
            return None
    else:
        # For route-format URLs, check that the path contains 'join'
        path = parsed.path or ""
        if not path.endswith("join") and path not in ("", "/"):
            return None

    params = parse_qs(parsed.query, keep_blank_values=False)
    code = (params.get("code", [""])[0]).strip()

    if not code:
        return None

    return {"code": code}


def decode_qr_data(data: str) -> Optional[dict]:
    """Decode QR string data. Returns dict with only 'code' key.
    
    Accepts both deep link URLs and JSON payloads for backward compatibility.
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
    if not code:
        return None

    return {"code": code}