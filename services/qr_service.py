"""QR Code generation and scanning service for WaterPilot invitations.

Provides:
- generate_invitation_qr(invitation) -> PIL Image containing QR with JSON payload
- decode_qr_image(image) -> dict | None (decoded payload)

The QR payload format:
{
  "code": "483921",
  "type": "worker",       # "worker" | "owner"
  "business_id": "uuid..."
}
"""
import json
from typing import Optional
import qrcode
from PIL import Image
import io
import base64


class QRDecodeError(Exception):
    pass


def generate_invitation_qr(code: str, invitation_type: str, business_id: str) -> Image.Image:
    """Generate a QR code image containing the invitation payload as JSON.
    
    Args:
        code: The 6-digit invitation code.
        invitation_type: "worker" or "owner".
        business_id: The UUID of the business.
    
    Returns:
        PIL Image of the QR code.
    """
    payload = json.dumps({
        "code": code,
        "type": invitation_type,
        "business_id": business_id,
    })
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img


def generate_invitation_qr_base64(code: str, invitation_type: str, business_id: str) -> str:
    """Generate QR code and return as a base64-encoded PNG string."""
    img = generate_invitation_qr(code, invitation_type, business_id)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def decode_qr_data(data: str) -> Optional[dict]:
    """Decode a QR string (JSON payload) into a dict.
    
    Expects valid JSON with keys: code, type, business_id.
    
    Returns:
        dict with parsed fields, or None if invalid.
    """
    if not data:
        return None
    try:
        payload = json.loads(data.strip())
    except (json.JSONDecodeError, ValueError):
        return None
    
    # Validate required fields
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