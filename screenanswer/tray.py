"""Notification-area tray: a silent colored sphere.

Product spec for v1:
- The icon is a sphere whose color IS the answer: red=1, yellow=2, green=3,
  blue=4, grey=ready/no answer. Color is the only runtime feedback.
- No hover tooltip, no balloon notifications — ever (silent shell).
- Left-click does nothing. Right-click shows exactly two entries:
  "Open GUI" and "Diagnostics console".
- Binds: Ctrl+Alt+S captures; Ctrl+Alt+O silently schedules deletion of the
  running executable and its config, then exits (no prompt, no notification).

`WindowsTray` is a simplified port of the proven v1.7 ctypes tray.
`NullShell` is the non-Windows / test stand-in with the same interface.
"""

from __future__ import annotations

import ctypes
import os
import queue
import threading
from typing import Any, Callable, Dict, Optional, Tuple

from .parser import NEUTRAL_RGB

HOTKEY_CAPTURE_ID = 1
HOTKEY_DELETE_ID = 2

RESULT_HOLD_MS = 10_000
FADE_DURATION_MS = 1_500
FADE_INTERVAL_MS = 300

# ---------------------------------------------------------------------------
# Win32 constants shared by the message thread and the helper methods.
# They live at module scope on purpose: methods like set_state() and
# _show_context_menu() must see them too (a function-scope constant is a
# NameError waiting to happen at click time).
# ---------------------------------------------------------------------------
WM_TRAY = 0x8000 + 41
WM_HOTKEY = 0x0312
WM_CLOSE = 0x0010
WM_DESTROY = 0x0002
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
WS_POPUP = 0x80000000
MF_STRING = 0x00000000
TPM_RETURNCMD = 0x0100
TPM_RIGHTBUTTON = 0x0002
CMD_OPEN = 102
CMD_DIAGNOSTICS = 104
TRAY_UID = 1


class POINT(ctypes.Structure):
    """Cursor position (Windows POINT). Module scope so every user shares one type."""

    _fields_ = [("x", ctypes.c_int32), ("y", ctypes.c_int32)]


class ShellBase:
    """Interface the app expects: colored state, balloons, lifecycle."""

    def set_state(self, rgb: Tuple[int, int, int], tooltip: str = "") -> None:
        raise NotImplementedError

    def show_balloon(self, title: str, message: str) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError


class NullShell(ShellBase):
    """Non-Windows/dev shell: records states, never touches the OS."""

    def __init__(self, on_event: Optional[Callable[[Tuple[Any, ...]], None]] = None) -> None:
        self.states = []
        self.balloons = []
        self._on_event = on_event

    def set_state(self, rgb: Tuple[int, int, int], tooltip: str = "") -> None:
        self.states.append((rgb, tooltip))

    def show_balloon(self, title: str, message: str) -> None:
        self.balloons.append((title, message))

    def stop(self) -> None:
        pass

    # Test helper: simulate a tray-menu / hotkey event.
    def emit(self, event: Tuple[Any, ...]) -> None:
        if self._on_event is not None:
            self._on_event(event)


class WindowsTray(ShellBase):
    """Small ctypes-based notification-area icon and global-hotkey host."""

    def __init__(self, events: "queue.Queue[Tuple[Any, ...]]") -> None:
        if os.name != "nt":
            raise RuntimeError("The Windows tray is available on Windows only.")
        self.events = events
        self.hwnd = None
        self._ready = threading.Event()
        self._lock = threading.RLock()
        self._startup_error: Optional[str] = None
        self._icons: Dict[Tuple[int, int, int], int] = {}
        self._nid = None
        self._thread = threading.Thread(
            target=self._message_thread_guarded,
            name="ScreenAnswerTray",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(10):
            raise RuntimeError("The Windows notification-area icon did not start.")
        if self._startup_error:
            raise RuntimeError(self._startup_error)

    def _message_thread_guarded(self) -> None:
        try:
            self._message_thread()
        except Exception as exc:
            if not self._ready.is_set():
                self._startup_error = "Could not initialize the Windows tray: %s" % exc
                self._ready.set()
            else:
                self.events.put(("fatal", "Windows tray stopped unexpectedly: %s" % exc))

    def _message_thread(self) -> None:
        from ctypes import wintypes as wt

        LRESULT = ctypes.c_ssize_t
        WPARAM = ctypes.c_size_t
        LPARAM = ctypes.c_ssize_t

        class GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", wt.DWORD),
                ("Data2", wt.WORD),
                ("Data3", wt.WORD),
                ("Data4", wt.BYTE * 8),
            ]

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wt.DWORD),
                ("hWnd", wt.HWND),
                ("uID", wt.UINT),
                ("uFlags", wt.UINT),
                ("uCallbackMessage", wt.UINT),
                ("hIcon", wt.HICON),
                ("szTip", wt.WCHAR * 128),
                ("dwState", wt.DWORD),
                ("dwStateMask", wt.DWORD),
                ("szInfo", wt.WCHAR * 256),
                ("uTimeoutOrVersion", wt.UINT),
                ("szInfoTitle", wt.WCHAR * 64),
                ("dwInfoFlags", wt.DWORD),
                ("guidItem", GUID),
                ("hBalloonIcon", wt.HICON),
            ]

        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, WPARAM, LPARAM)

        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wt.UINT),
                ("style", wt.UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wt.HINSTANCE),
                ("hIcon", wt.HICON),
                ("hCursor", wt.HANDLE),
                ("hbrBackground", wt.HBRUSH),
                ("lpszMenuName", wt.LPCWSTR),
                ("lpszClassName", wt.LPCWSTR),
                ("hIconSm", wt.HICON),
            ]

        class_name = "ScreenAnswerTrayWindow_%x" % id(self)
        self._class_name = class_name
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._user32 = user32
        self._shell32 = shell32
        self._gdi32 = gdi32
        self._nid_type = NOTIFYICONDATAW

        user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, WPARAM, LPARAM]
        user32.DefWindowProcW.restype = LRESULT
        user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
        user32.RegisterClassExW.restype = wt.ATOM
        user32.CreateWindowExW.argtypes = [
            wt.DWORD,
            wt.LPCWSTR,
            wt.LPCWSTR,
            wt.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wt.HWND,
            wt.HMENU,
            wt.HINSTANCE,
            ctypes.c_void_p,
        ]
        user32.CreateWindowExW.restype = wt.HWND
        user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
        user32.GetMessageW.restype = ctypes.c_int
        user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
        user32.PostQuitMessage.argtypes = [ctypes.c_int]
        user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, WPARAM, LPARAM]
        user32.RegisterHotKey.argtypes = [wt.HWND, ctypes.c_int, wt.UINT, wt.UINT]
        user32.RegisterHotKey.restype = wt.BOOL
        user32.UnregisterHotKey.argtypes = [wt.HWND, ctypes.c_int]
        user32.UnregisterHotKey.restype = wt.BOOL
        user32.CreatePopupMenu.restype = wt.HMENU
        user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
        user32.AppendMenuW.restype = wt.BOOL
        user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.HWND, ctypes.c_void_p]
        user32.TrackPopupMenu.restype = ctypes.c_uint
        user32.DestroyMenu.argtypes = [wt.HMENU]
        user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
        user32.SetForegroundWindow.argtypes = [wt.HWND]
        user32.DestroyWindow.argtypes = [wt.HWND]
        user32.DestroyIcon.argtypes = [wt.HICON]
        user32.DestroyIcon.restype = wt.BOOL
        user32.UnregisterClassW.argtypes = [wt.LPCWSTR, wt.HINSTANCE]
        shell32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
        shell32.Shell_NotifyIconW.restype = wt.BOOL
        kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wt.HMODULE

        def window_proc(hwnd: int, message: int, wparam: int, lparam: int) -> int:
            if message == WM_HOTKEY:
                if wparam == HOTKEY_CAPTURE_ID:
                    self.events.put(("capture",))
                    return 0
                if wparam == HOTKEY_DELETE_ID:
                    self.events.put(("delete",))
                    return 0
            elif message == WM_TRAY:
                event = int(lparam) & 0xFFFF
                if event == WM_RBUTTONUP:
                    self._show_context_menu(hwnd)
                    return 0
                # Left-click / double-click: deliberately silent (spec: only
                # right-click reveals the menu). Swallow the message.
                if event in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    return 0
            elif message == WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            elif message == WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        # Keep the callback alive for the lifetime of the native window.
        self._wndproc = WNDPROC(window_proc)
        wndclass = WNDCLASSEXW()
        wndclass.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wndclass.lpfnWndProc = self._wndproc
        wndclass.hInstance = kernel32.GetModuleHandleW(None)
        wndclass.lpszClassName = class_name
        if not user32.RegisterClassExW(ctypes.byref(wndclass)):
            raise RuntimeError("RegisterClassExW failed for the tray window.")

        hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "ScreenAnswerTrayWindow",
            WS_POPUP,
            0,
            0,
            0,
            0,
            None,
            None,
            wndclass.hInstance,
            None,
        )
        if not hwnd:
            error_code = ctypes.get_last_error()
            raise RuntimeError("CreateWindowExW failed (Windows error %s)." % error_code)
        self.hwnd = hwnd

        self._nid = NOTIFYICONDATAW()
        self._nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self._nid.hWnd = hwnd
        self._nid.uID = TRAY_UID
        # Silent sphere: no NIF_TIP — Windows shows no hover tooltip.
        self._nid.uFlags = NIF_MESSAGE | NIF_ICON
        self._nid.uCallbackMessage = WM_TRAY
        self._nid.hIcon = self._create_icon(NEUTRAL_RGB)
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self._nid)):
            error_code = ctypes.get_last_error()
            self._ready.set()
            raise RuntimeError("Shell_NotifyIconW could not add the icon (%s)." % error_code)

        for hotkey_id, modifiers, key in (
            (HOTKEY_CAPTURE_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, ord("S")),
            (HOTKEY_DELETE_ID, MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, ord("O")),
        ):
            user32.RegisterHotKey(hwnd, hotkey_id, modifiers, key)

        self._ready.set()
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        self._cleanup_icons()

    def _show_context_menu(self, hwnd: int) -> None:
        """Right-click menu — exactly two entries per spec."""
        user32 = self._user32
        menu = user32.CreatePopupMenu()
        if not menu:
            return
        try:
            user32.AppendMenuW(menu, MF_STRING, CMD_OPEN, "Open GUI")
            user32.AppendMenuW(menu, MF_STRING, CMD_DIAGNOSTICS, "Diagnostics console")
            point = POINT()
            user32.GetCursorPos(ctypes.byref(point))
            user32.SetForegroundWindow(hwnd)
            command = user32.TrackPopupMenu(
                menu,
                TPM_RETURNCMD | TPM_RIGHTBUTTON,
                point.x,
                point.y,
                0,
                hwnd,
                None,
            )
        finally:
            user32.DestroyMenu(menu)
        if command == CMD_OPEN:
            self.events.put(("open",))
        elif command == CMD_DIAGNOSTICS:
            self.events.put(("diagnostics",))

    def _create_icon(self, rgb: Tuple[int, int, int]) -> int:
        """Build a small alpha-blended circle icon via GDI; no icon asset needed."""
        import ctypes
        import math
        from ctypes import wintypes as wt

        with self._lock:
            cached = self._icons.get(rgb)
            if cached:
                return cached

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

        class ICONINFO(ctypes.Structure):
            _fields_ = [
                ("fIcon", wt.BOOL),
                ("xHotspot", wt.DWORD),
                ("yHotspot", wt.DWORD),
                ("hbmMask", wt.HBITMAP),
                ("hbmColor", wt.HBITMAP),
            ]

        SIZE = 16
        user32 = self._user32
        gdi32 = self._gdi32
        gdi32.CreateDIBSection.argtypes = [
            wt.HDC,
            ctypes.POINTER(BITMAPINFO),
            wt.UINT,
            ctypes.POINTER(ctypes.c_void_p),
            wt.HANDLE,
            wt.DWORD,
        ]
        gdi32.CreateDIBSection.restype = wt.HBITMAP
        gdi32.CreateBitmap.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            wt.UINT,
            wt.UINT,
            ctypes.c_void_p,
        ]
        gdi32.CreateBitmap.restype = wt.HBITMAP
        gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
        gdi32.DeleteObject.restype = wt.BOOL
        user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
        user32.CreateIconIndirect.restype = wt.HICON

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = SIZE
        bmi.bmiHeader.biHeight = -SIZE
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0
        bmi.bmiHeader.biSizeImage = SIZE * SIZE * 4
        pixel_pointer = ctypes.c_void_p()
        color_bitmap = gdi32.CreateDIBSection(
            None,
            ctypes.byref(bmi),
            0,
            ctypes.byref(pixel_pointer),
            None,
            0,
        )
        if not color_bitmap or not pixel_pointer.value:
            raise RuntimeError("Windows could not create the tray icon bitmap.")

        # For the 1-bit AND mask, outside-circle pixels are transparent (white).
        mask_data = bytearray(2 * SIZE)  # 1-bpp CreateBitmap rows are word-aligned.
        for y in range(SIZE):
            for x in range(SIZE):
                if math.hypot(x - 7.5, y - 7.5) > 7.45:
                    mask_data[y * 2 + x // 8] |= 0x80 >> (x % 8)
        mask_buffer = ctypes.create_string_buffer(bytes(mask_data))
        mask_bitmap = gdi32.CreateBitmap(
            SIZE, SIZE, 1, 1, ctypes.cast(mask_buffer, ctypes.c_void_p)
        )
        if not mask_bitmap:
            gdi32.DeleteObject(color_bitmap)
            raise RuntimeError("Windows could not create the tray icon mask.")

        pixels = (ctypes.c_uint32 * (SIZE * SIZE)).from_address(pixel_pointer.value)
        red, green, blue = rgb
        for y in range(SIZE):
            for x in range(SIZE):
                distance = math.hypot(x - 7.5, y - 7.5)
                if distance > 7.45:
                    pixels[y * SIZE + x] = 0x00000000
                elif distance >= 5.8:
                    pixels[y * SIZE + x] = 0xFFFFFFFF
                else:
                    # DIB pixels are stored as BGRA on little-endian Windows.
                    pixels[y * SIZE + x] = (0xFF << 24) | (red << 16) | (green << 8) | blue

        icon_info = ICONINFO()
        icon_info.fIcon = True
        icon_info.xHotspot = 0
        icon_info.yHotspot = 0
        icon_info.hbmMask = mask_bitmap
        icon_info.hbmColor = color_bitmap
        icon = user32.CreateIconIndirect(ctypes.byref(icon_info))
        gdi32.DeleteObject(mask_bitmap)
        gdi32.DeleteObject(color_bitmap)
        if not icon:
            raise RuntimeError("Windows could not create the colored tray icon.")
        with self._lock:
            self._icons[rgb] = icon
        return icon

    def _cleanup_icons(self) -> None:
        with self._lock:
            icons = list(self._icons.values())
            if self._nid is not None and self._nid.hIcon:
                icons.append(self._nid.hIcon)
            self._icons.clear()
        for icon in icons:
            try:
                self._user32.DestroyIcon(icon)
            except Exception:
                pass

    def set_state(self, rgb: Tuple[int, int, int], tooltip: str = "") -> None:
        """Change the sphere color. `tooltip` is ignored — the shell is silent."""
        if not self._nid or not self.hwnd:
            return
        with self._lock:
            self._nid.hIcon = self._create_icon(rgb)
            self._nid.uFlags = 0x00000001 | 0x00000002  # MESSAGE|ICON only; no NIF_TIP
        self._shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self._nid))

    def show_balloon(self, title: str, message: str) -> None:
        """Silent shell: no balloon notifications, ever. Color is the feedback."""
        return

    def stop(self) -> None:
        if self.hwnd:
            self._user32.PostMessageW(self.hwnd, 0x0010, 0, 0)  # WM_CLOSE
        if self._nid is not None:
            try:
                self._shell32.Shell_NotifyIconW(0x00000002, ctypes.byref(self._nid))  # NIM_DELETE
            except Exception:
                pass


def create_shell(events: "queue.Queue[Tuple[Any, ...]]") -> ShellBase:
    """Windows gets the real tray; everything else gets NullShell."""
    if os.name == "nt":
        return WindowsTray(events)
    return NullShell()
