"""Silent self-deletion (the `Ctrl+Alt+O` bind).

Ported from the v1.7 Lasso scoped self-cleanup and adapted to v1:

- Deletes ONLY the running frozen executable and its matching sidecar
  config (`screen_answer_config.json`). Nothing else is ever touched; a
  directory is removed only when it is empty afterwards.
- Silent: no prompt, no notification, no window. The tray icon simply
  disappears when the process exits.
- If cleanup cannot be scheduled, this returns False and the app must
  stay open.
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
from typing import Optional

from .config import PORTABLE_CONFIG_NAME, portable_config_path


def _powershell_string_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _build_cleanup_script(exe_path: str, config_path: str, config_directory: str) -> str:
    """The detached PowerShell that removes exe + config once the process exits."""
    return """
$ErrorActionPreference = 'SilentlyContinue'
$exePath = %s
$configPath = %s
$configDirectory = %s
Start-Sleep -Seconds 2
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if (-not (Test-Path -LiteralPath $exePath)) { break }
    try {
        Remove-Item -LiteralPath $exePath -Force -ErrorAction Stop
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}
try {
    if (Test-Path -LiteralPath $configPath) {
        Remove-Item -LiteralPath $configPath -Force -ErrorAction Stop
    }
} catch {}
try {
    if (Test-Path -LiteralPath $configDirectory -PathType Container) {
        $remaining = @(Get-ChildItem -LiteralPath $configDirectory -Force -ErrorAction SilentlyContinue)
        if ($remaining.Count -eq 0) {
            Remove-Item -LiteralPath $configDirectory -Force -ErrorAction SilentlyContinue
        }
    }
} catch {}
""" % (
        _powershell_string_literal(exe_path),
        _powershell_string_literal(config_path),
        _powershell_string_literal(config_directory),
    )


def _valid_config_path(config_path: str) -> bool:
    # Accept both separators so validation works on any host OS.
    name = config_path.replace("\\", "/").rsplit("/", 1)[-1]
    return name.lower() == PORTABLE_CONFIG_NAME.lower()


def _is_frozen_exe(exe_path: str) -> bool:
    return exe_path.lower().endswith(".exe")


def schedule_silent_deletion(
    executable_path: Optional[str] = None,
    config_path: Optional[str] = None,
) -> bool:
    """Delete the running app and its config, silently.

    Returns True when cleanup is done (source run) or scheduled (frozen
    Windows run). Returns False when nothing safe can be done — the caller
    must then keep the app open.
    """
    exe_path = os.path.abspath(executable_path if executable_path is not None else sys.executable)
    frozen = bool(getattr(sys, "frozen", False)) or executable_path is not None
    config = os.path.abspath(config_path or portable_config_path())

    if not _valid_config_path(config):
        return False

    if not frozen:
        # Source run: there is no bundled executable to remove; delete only
        # the sidecar config, silently.
        try:
            os.remove(config)
        except OSError:
            pass
        return True

    if not _is_frozen_exe(exe_path):
        return False
    if os.name != "nt":
        return False

    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    powershell_path = os.path.join(
        system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"
    )
    if not os.path.isfile(powershell_path):
        return False

    config_directory = os.path.dirname(config)
    cleanup_script = _build_cleanup_script(exe_path, config, config_directory)
    try:
        encoded_script = base64.b64encode(cleanup_script.encode("utf-16le")).decode("ascii")
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = 0
        subprocess.Popen(
            [
                powershell_path,
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle",
                "Hidden",
                "-EncodedCommand",
                encoded_script,
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            startupinfo=startup_info,
        )
    except (OSError, UnicodeError, AttributeError, ValueError, subprocess.SubprocessError):
        return False
    return True
