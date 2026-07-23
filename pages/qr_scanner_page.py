"""QR Scanner page for WaterPilot.

Opens the camera, scans continuously for a valid WaterPilot invitation QR,
and returns the decoded data on success.

Uses OpenCV for camera capture and pyzbar for QR decoding.
The camera feed is displayed as a dynamically updated base64 image in Flet.
"""
import asyncio
import threading
import json
import base64
import sys
import traceback
from typing import Optional, Callable
import flet as ft
import theme
from services.qr_service import decode_qr_data

# Optional camera imports — fail gracefully if not available
try:
    import cv2
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False

##try:
   ## from pyzbar.pyzbar import decode as pyzbar_decode
   ## HAS_PYZBAR = True
##except ImportError:
HAS_PYZBAR = False
pyzbar_decode = False


SCAN_INTERVAL = 0.15  # seconds between frame captures


def build_qr_scanner(page: ft.Page,
                     on_scan_success: Callable[[dict], None],
                     on_back: Callable,
                     services=None) -> ft.Container:
    """Build the QR scanner page.
    
    Args:
        on_scan_success: Called with decoded QR dict when a valid QR is found.
        on_back: Called when user taps back button.
        services: App services (used for optional validation feedback).
    """
    
    if not HAS_CV2 or not HAS_PYZBAR:
        return _build_no_camera_page(page, on_back)
    
    # --- State ---
    camera = None
    scanning_active = True
    scan_finished = False
    camera_thread: Optional[threading.Thread] = None
    
    # --- UI elements ---
    status_text = ft.Text(
        "Position QR code in the frame",
        size=13, color=theme.TEXT_MID, text_align=ft.TextAlign.CENTER,
    )
    error_text = ft.Text("", size=12, color=theme.DANGER, visible=False, text_align=ft.TextAlign.CENTER)
    loading = ft.ProgressRing(width=24, height=24, stroke_width=2.5, color=theme.ACCENT, visible=False)
    
    # Camera feed display
    camera_image = ft.Image(
        src="",  # Will be set to base64 data URI
        width=320,
        height=240,
        fit="contain",
        border_radius=12,
    )
    
    # Back button
    back_button = ft.TextButton(
        "← Back",
        on_click=lambda e: _cleanup_and_go_back(),
        style=ft.ButtonStyle(color=theme.ACCENT),
    )
    
    # --- Camera thread ---
    def _camera_loop():
        nonlocal camera, scan_finished, scanning_active
        
        # Try to open camera with various backends
        camera = None
        for backend in (cv2.CAP_DSHOW, cv2.CAP_ANY):
            try:
                cam = cv2.VideoCapture(0, backend)
                if cam.isOpened():
                    camera = cam
                    break
            except Exception:
                continue
        
        if camera is None:
            asyncio.run_coroutine_threadsafe(
                _show_error("Could not open camera. Check permissions."),
                page.loop,
            )
            return
        
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        frame_count = 0
        
        while scanning_active and not scan_finished:
            try:
                ret, frame = camera.read()
                if not ret or frame is None:
                    continue
                
                frame_count += 1
                
                # Decode QR from every 3rd frame for performance
                if frame_count % 3 == 0:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    decoded_objects = pyzbar_decode(gray)
                    
                    for obj in decoded_objects:
                        qr_data = obj.data.decode("utf-8", errors="replace")
                        decoded = decode_qr_data(qr_data)
                        
                        if decoded is not None:
                            scan_finished = True
                            
                            # Draw a green box around the QR
                            if len(obj.polygon) > 0:
                                pts = [(p.x, p.y) for p in obj.polygon]
                                import numpy as np
                                pts_np = np.array(pts, dtype=np.int32)
                                cv2.polylines(frame, [pts_np], True, (0, 255, 0), 3)
                            
                            _update_camera_feed(frame)
                            
                            asyncio.run_coroutine_threadsafe(
                                _on_scan_complete(decoded),
                                page.loop,
                            )
                            return
                
                # Draw crosshair overlay
                h, w = frame.shape[:2]
                cx, cy = w // 2, h // 2
                cv2.line(frame, (cx - 30, cy), (cx + 30, cy), (0, 255, 255), 2)
                cv2.line(frame, (cx, cy - 30), (cx, cy + 30), (0, 255, 255), 2)
                
                _update_camera_feed(frame)
                
            except Exception as exc:
                if scanning_active:
                    asyncio.run_coroutine_threadsafe(
                        _show_error(f"Camera error: {str(exc)[:50]}"),
                        page.loop,
                    )
                break
            
            threading.Event().wait(SCAN_INTERVAL)
    
    def _update_camera_feed(frame):
        """Convert OpenCV frame to base64 and update the UI."""
        try:
            _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            b64 = base64.b64encode(buffer).decode("utf-8")
            
            async def _update():
                if not scan_finished:
                    camera_image.src = f"data:image/jpeg;base64,{b64}"
                    page.update()
            
            asyncio.run_coroutine_threadsafe(_update(), page.loop)
        except Exception:
            pass
    
    async def _on_scan_complete(decoded: dict):
        nonlocal scan_finished
        status_text.value = "✓ QR Code detected!"
        status_text.color = theme.SUCCESS
        loading.visible = True
        page.update()
        
        await asyncio.sleep(0.3)
        
        _release_camera()
        
        on_scan_success(decoded)
    
    async def _show_error(msg: str):
        nonlocal scan_finished
        scan_finished = True
        error_text.value = msg
        error_text.visible = True
        status_text.value = "Camera unavailable"
        status_text.color = theme.DANGER
        loading.visible = False
        _release_camera()
        page.update()
    
    def _release_camera():
        nonlocal camera
        if camera is not None:
            try:
                camera.release()
            except Exception:
                pass
            camera = None
    
    def _cleanup_and_go_back():
        nonlocal scanning_active, scan_finished
        scanning_active = False
        scan_finished = True
        _release_camera()
        on_back()
    
    def _start_camera():
        nonlocal camera_thread
        camera_thread = threading.Thread(target=_camera_loop, daemon=True)
        camera_thread.start()
    
    # --- Build UI ---
    scanner_view = ft.Container(
        content=ft.Column([
            ft.Row([
                back_button,
                ft.Container(expand=True),
                ft.Icon(ft.Icons.QR_CODE_SCANNER, color=theme.ACCENT, size=24),
                ft.Container(expand=True),
            ]),
            
            ft.Container(height=8),
            
            ft.Stack([
                ft.Container(
                    content=camera_image,
                    alignment=ft.Alignment.CENTER,
                    border_radius=12,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                ),
                ft.Container(
                    content=ft.Container(
                        width=220, height=220,
                        border=ft.Border.all(2.5, theme.ACCENT),
                        border_radius=16,
                        alignment=ft.Alignment.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                ),
            ], width=320, height=240),
            
            ft.Container(height=16),
            
            status_text,
            error_text,
            
            ft.Container(height=8),
            ft.Container(content=loading, alignment=ft.Alignment.CENTER),
            
            ft.Container(height=12),
            
            ft.Text(
                "Scan the QR code from your employer's invitation",
                size=11, color=theme.TEXT_DIM, text_align=ft.TextAlign.CENTER,
            ),
        ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.Padding(20, 12, 20, 20),
        expand=True,
    )
    
    page.run_task(_delayed_start, _start_camera)
    
    return scanner_view


async def _delayed_start(start_callback):
    await asyncio.sleep(0.1)
    start_callback()


def _build_no_camera_page(page: ft.Page, on_back: Callable) -> ft.Container:
    """Fallback page when camera dependencies are not available."""
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.TextButton("← Back", on_click=lambda e: on_back(),
                              style=ft.ButtonStyle(color=theme.ACCENT)),
            ]),
            ft.Container(height=40),
            ft.Icon(ft.Icons.QR_CODE_SCANNER, size=64, color=theme.TEXT_DIM),
            ft.Container(height=16),
            ft.Text(
                "Camera not available",
                size=20, weight=ft.FontWeight.BOLD, color=theme.text_primary(),
            ),
            ft.Text(
                "QR scanning requires a camera. "
                "Please enter your invitation code manually.",
                size=13, color=theme.TEXT_DIM, text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=16),
            ft.ElevatedButton(
                "Enter Code Manually",
                on_click=lambda e: on_back(),
                style=ft.ButtonStyle(
                    bgcolor=theme.ACCENT,
                    color=ft.Colors.BLACK,
                    shape=ft.RoundedRectangleBorder(radius=theme.RADIUS_INPUT),
                    padding=ft.Padding(24, 16, 24, 16),
                ),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
        padding=20,
        alignment=ft.Alignment.CENTER,
        expand=True,
    )