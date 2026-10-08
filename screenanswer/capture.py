"""Desktop capture → PNG bytes, held only in process memory.

Ported from the v1.7 `answer_tray.py` implementation: full Windows virtual
desktop via GDI, top-down 24-bit rows, stdlib PNG encoder, hard caps on
pixels and PNG size. Non-Windows platforms raise CaptureUnavailable (v1
targets Windows; the rest of the code is testable anywhere).
"""

from __future__ import annotations

import binascii
import os
import struct
import zlib

MAX_SCREEN_PIXELS = 24_000_000
MAX_PNG_BYTES = 12 * 1024 * 1024


class CaptureUnavailable(RuntimeError):
    pass


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", binascii.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def encode_rgb_png(width: int, height: int, bgr_pixels: bytes, stride: int) -> bytes:
    """Encode top-down 24-bit BGR rows (as returned by GetDIBits) as a PNG."""
    if width <= 0 or height <= 0:
        raise CaptureUnavailable("Windows reported an invalid desktop size.")
    row_bytes = width * 3
    expected = stride * height
    if len(bgr_pixels) < expected:
        raise CaptureUnavailable("Windows returned an incomplete screen capture.")

    raw = bytearray()
    for y in range(height):
        start = y * stride
        bgr = memoryview(bgr_pixels)[start : start + row_bytes]
        rgb = bytearray(row_bytes)
        rgb[0::3] = bgr[2::3]
        rgb[1::3] = bgr[1::3]
        rgb[2::3] = bgr[0::3]
        raw.append(0)  # PNG filter: None
        raw.extend(rgb)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(_png_chunk(b"IHDR", ihdr))
    png.extend(_png_chunk(b"IDAT", zlib.compress(bytes(raw), level=6)))
    png.extend(_png_chunk(b"IEND", b""))
    if len(png) > MAX_PNG_BYTES:
        raise CaptureUnavailable(
            "The screenshot is too large to send in one vision API request. "
            "Try reducing the desktop resolution or disconnecting an extra monitor."
        )
    return bytes(png)


def capture_virtual_desktop_png() -> bytes:
    """Capture all Windows monitors into a PNG held only in process memory."""
    if os.name != "nt":
        raise CaptureUnavailable("Screen capture is supported on Windows only.")

    import ctypes
    from ctypes import wintypes as wt

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    class RGBQUAD(ctypes.Structure):
        _fields_ = [
            ("rgbBlue", wt.BYTE),
            ("rgbGreen", wt.BYTE),
            ("rgbRed", wt.BYTE),
            ("rgbReserved", wt.BYTE),
        ]

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wt.DWORD),
            ("biWidth", wt.LONG),
            ("biHeight", wt.LONG),
            ("biPlanes", wt.WORD),
            ("biBitCount", wt.WORD),
            ("biCompression", wt.DWORD),
            ("biSizeImage", wt.DWORD),
            ("biXPelsPerMeter", wt.LONG),
            ("biYPelsPerMeter", wt.LONG),
            ("biClrUsed", wt.DWORD),
            ("biClrImportant", wt.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]

    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetDC.argtypes = [wt.HWND]
    user32.GetDC.restype = wt.HDC
    user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
    gdi32.CreateCompatibleDC.restype = wt.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wt.HBITMAP
    gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
    gdi32.SelectObject.restype = wt.HGDIOBJ
    gdi32.BitBlt.argtypes = [
        wt.HDC,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wt.HDC,
        ctypes.c_int,
        ctypes.c_int,
        wt.DWORD,
    ]
    gdi32.BitBlt.restype = wt.BOOL
    gdi32.GetDIBits.argtypes = [
        wt.HDC,
        wt.HBITMAP,
        wt.UINT,
        wt.UINT,
        ctypes.c_void_p,
        ctypes.POINTER(BITMAPINFO),
        wt.UINT,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
    gdi32.DeleteObject.restype = wt.BOOL
    gdi32.DeleteDC.argtypes = [wt.HDC]
    gdi32.DeleteDC.restype = wt.BOOL

    try:
        user32.SetProcessDPIAware()
    except (AttributeError, OSError):
        pass
    left = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    top = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    if width <= 0 or height <= 0:
        raise CaptureUnavailable("Could not determine the desktop dimensions.")
    if width * height > MAX_SCREEN_PIXELS:
        raise CaptureUnavailable(
            "The combined desktop is too large for this lightweight capture path."
        )

    screen_dc = user32.GetDC(None)
    if not screen_dc:
        raise CaptureUnavailable("Could not access the Windows desktop.")
    memory_dc = None
    bitmap = None
    old_bitmap = None
    try:
        memory_dc = gdi32.CreateCompatibleDC(screen_dc)
        if not memory_dc:
            raise CaptureUnavailable("Could not create a screen capture buffer.")
        bitmap = gdi32.CreateCompatibleBitmap(screen_dc, width, height)
        if not bitmap:
            raise CaptureUnavailable("Could not allocate the screen capture bitmap.")
        old_bitmap = gdi32.SelectObject(memory_dc, bitmap)
        if not old_bitmap:
            raise CaptureUnavailable("Could not initialize the screen capture bitmap.")
        if not gdi32.BitBlt(
            memory_dc,
            0,
            0,
            width,
            height,
            screen_dc,
            left,
            top,
            0x00CC0020 | 0x40000000,  # SRCCOPY | CAPTUREBLT
        ):
            raise CaptureUnavailable("Windows could not copy the desktop into memory.")
        gdi32.SelectObject(memory_dc, old_bitmap)
        old_bitmap = None

        stride = ((width * 24 + 31) // 32) * 4
        image_size = stride * height
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = width
        bmi.bmiHeader.biHeight = -height  # top-down rows
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 24
        bmi.bmiHeader.biCompression = 0  # BI_RGB
        bmi.bmiHeader.biSizeImage = image_size
        buffer = ctypes.create_string_buffer(image_size)
        rows = gdi32.GetDIBits(
            screen_dc,
            bitmap,
            0,
            height,
            ctypes.cast(buffer, ctypes.c_void_p),
            ctypes.byref(bmi),
            0,  # DIB_RGB_COLORS
        )
        if rows != height:
            raise CaptureUnavailable("Windows returned an incomplete screen capture.")
        return encode_rgb_png(width, height, buffer.raw, stride)
    finally:
        if old_bitmap and memory_dc:
            gdi32.SelectObject(memory_dc, old_bitmap)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory_dc:
            gdi32.DeleteDC(memory_dc)
        user32.ReleaseDC(None, screen_dc)
