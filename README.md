# Screen Answer

A small, user-triggered Windows study helper. It uses only Python's standard library at runtime (including Tkinter from the official Python installer) and the Windows APIs through `ctypes`; there are no `pip` runtime dependencies.

## Privacy and behavior

- The app has a **visible notification-area (system tray) icon**. It is not a stealth/hidden process and it does not install itself to Windows startup.
- A screenshot is taken only after the user presses **Ctrl+Alt+S**, clicks **Capture & ask now**, or selects **Capture and ask** from the tray menu.
- Every capture includes the **entire virtual desktop / all monitors**. The app shows a tray notification and sends that image over HTTPS to Google Gemini for an AI-only response. **Live web search / Google Search grounding is disabled.** The image is held in memory and is not written to a screenshot file.
- The user supplies their own Gemini API key. By default it stays in memory for that run. An optional checkbox saves it, along with the model, in `screen_answer_config.json` beside the app so the EXE and sidecar can be copied to another device. That sidecar is **plain text** and is not included in the release; keep it private and never upload it to GitHub or share it. `GEMINI_API_KEY` may also be set in the environment. The app still requires acknowledging the upload notice on each run.
- Use this only with screen content you are allowed to share with Google and where AI assistance is permitted. Gemini can be wrong; the tray color is a suggestion, not a guarantee.
- There is no self-destruct or file-deletion hotkey. **Ctrl+Alt+Q** and the tray menu's **Exit** command close the app normally. Remove the downloaded `.exe` or source folder yourself if you want to uninstall it.

## Use

1. Run `answer_tray.py` (or the packaged `ScreenAnswer.exe`). A grey icon appears in the Windows notification area. Windows may place it in the tray overflow/hidden-icons menu; you can pin it in taskbar notification-area settings.
2. Double-click the tray icon to open settings. Enter a Gemini API key, confirm the full-screen upload notice, and click **Save settings**. Leave the portable-config checkbox clear to keep the key in memory only, or check it to write `screen_answer_config.json` beside the app. For portable mode, keep the app in a writable folder (such as Downloads or a USB drive), not a protected Program Files folder.
   To move to a laptop, copy both `ScreenAnswer.exe` and `screen_answer_config.json`. The sidecar preloads the key, so you don't need to sign in to Google in a browser on the laptop; the laptop still needs internet access and the key's Gemini quota must be available. Treat the sidecar like a password—it is plain text and must stay private.
3. Press **Ctrl+Alt+S** to capture and ask Gemini, or use **Capture & ask now**. The tray icon changes to the returned option:
   - Red: option 1
   - Yellow: option 2
   - Green: option 3
   - Blue: option 4
   - Grey: neutral / no reliable answer / ready
4. A result stays at full color for 10 seconds, then fades to grey over about 1.5 seconds. **Ctrl+Alt+Q** exits.

The model is set to `gemini-3.8-flash` by default and can be changed in the settings window. The model answers from the screenshot and its existing knowledge; it does not look up current facts on the web. A Gemini API key, internet access, and available Google API quota are required. Free-tier eligibility and quotas, API pricing, and model names can change.

## Diagnostic test build

The `ScreenAnswer-Diagnostic.exe` release build opens a live diagnostics window at startup. It shows startup/configuration state, whether the global hotkeys registered, capture dimensions and timing, each Gemini HTTP attempt and status, retry delays, network failures, response parsing, and the final tray result. Use **Open settings** in that window to enter a key and acknowledge the upload notice; capture still requires your explicit action.

This is a diagnostic build of the real app, **not a simulation**: after consent and a capture hotkey/button, it captures the full desktop and sends the screenshot to Gemini just like the regular build. The diagnostics log intentionally excludes the API key, screenshot pixels, and raw Gemini response text. You can save or copy the log from the diagnostics window; review it before sharing. Screenshots are not written to disk.

For a source run, use `python answer_tray.py --diagnostics`. Right-click the diagnostic build's tray icon and choose **Show diagnostics** if you close the window. If you use the portable config sidecar, keep `ScreenAnswer-Diagnostic.exe` beside `screen_answer_config.json`; otherwise enter the key in its Settings window. Keep `ScreenAnswer.exe` for normal use; the diagnostic build is a separate test executable.

## Run from source

- **Windows 10:** Python 3.8 or later with Tcl/Tk included.
- **Windows 7:** use Python 3.8.10 (the last Python release supporting Windows 7), on Windows 7 SP1 with current system updates. Select Tcl/Tk in the official Python installer.

Then launch it without a console window:

```powershell
pythonw answer_tray.py
```

The app window stays minimized to the **visible tray icon**. Use `python answer_tray.py` instead if you want a console for diagnostics. The app uses only the Python standard library. Tests for answer parsing and in-memory PNG encoding can be run on any platform:

```powershell
python -m unittest discover -s tests -v
```

## Build a standalone Windows executable

A one-file executable can be built without adding dependencies to the end user's PC. PyInstaller is needed only on the build machine:

```powershell
python -m pip install pyinstaller==5.13.2
pyinstaller --noconfirm --onefile --windowed --name ScreenAnswer answer_tray.py
```

The result is `dist/ScreenAnswer.exe`. For the best chance of Windows 7 compatibility, build with 32-bit Python 3.8.10 and test the executable on Windows 7 SP1; the source is also available for users who already have Python installed.

The GitHub Actions workflow in `.github/workflows/windows-release.yml` builds a 32-bit executable. Run it manually from **Actions → Build Windows release**, or push a version tag such as `v1.0.0` to attach the executable to a GitHub Release.
