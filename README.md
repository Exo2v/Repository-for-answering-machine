# Screen Answer

A small, user-triggered Windows study helper. It uses only Python's standard library at runtime (including Tkinter from the official Python installer) and the Windows APIs through `ctypes`; there are no `pip` runtime dependencies.

## Privacy and behavior

- The app has a **visible notification-area (system tray) icon**. It is not a stealth/hidden process and it does not install itself to Windows startup.
- A screenshot is taken only after the user presses **Ctrl+Alt+S**, clicks **Capture & ask now**, or selects **Capture and ask** from the tray menu.
- Every capture includes the **entire virtual desktop / all monitors**. The app shows a tray notification and sends that image over HTTPS to the Google Gemini API with Google Search grounding. The image is held in memory and is not written to a screenshot file.
- The user enters their own Gemini API key. The key is kept in memory for that run only; it is not saved in a config file. `GEMINI_API_KEY` may also be set in the environment, but the app still requires acknowledging the upload notice in its window.
- Use this only with screen content you are allowed to share with Google and where AI assistance is permitted. Gemini can be wrong; the tray color is a suggestion, not a guarantee.
- There is no self-destruct or file-deletion hotkey. **Ctrl+Alt+Q** and the tray menu's **Exit** command close the app normally. Remove the downloaded `.exe` or source folder yourself if you want to uninstall it.

## Use

1. Run `answer_tray.py` (or the packaged `ScreenAnswer.exe`). A grey icon appears in the Windows notification area. Windows may place it in the tray overflow/hidden-icons menu; you can pin it in taskbar notification-area settings.
2. Double-click the tray icon to open settings. Enter a Gemini API key, confirm the full-screen upload notice, and click **Save for this run**. The key is not persisted.
3. Press **Ctrl+Alt+S** to capture and ask Gemini, or use **Capture & ask now**. The tray icon changes to the returned option:
   - Red: option 1
   - Yellow: option 2
   - Green: option 3
   - Blue: option 4
   - Grey: neutral / no reliable answer / ready
4. A result stays at full color for 10 seconds, then fades to grey over about 1.5 seconds. **Ctrl+Alt+Q** exits.

The model is set to `gemini-3.8-flash` by default and can be changed in the settings window. A Gemini API key, internet access, and available Google API quota are required. Google API availability, pricing, and model names can change.

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
