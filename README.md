# Screen Answer

A small, user-triggered Windows study helper. The default app uses Python's standard library (including Tkinter from the official Python installer) and Windows APIs through `ctypes`; no `pip` runtime dependencies are required. The experimental Pix2Text build bundles its Python runtime and OCR dependencies, but downloads model weights on first use.

## Privacy and behavior

- The app has a **visible notification-area (system tray) icon**. It does not hide itself or install itself at Windows startup.
- A screenshot is captured only after **Ctrl+Alt+S**, **Capture & ask now**, or the tray menu's **Capture and ask** action.
- Each capture includes the **entire virtual desktop / all monitors**. The PNG is kept in memory and sent over HTTPS to the **selected provider**. It is not written to a screenshot file.
- Choose **Google Gemini** or **Mistral** in Settings. **Live web search and search/agent tools are not enabled.** Each provider needs its own API key. `GEMINI_API_KEY` and `MISTRAL_API_KEY` environment variables are supported. By default, Gemini receives the screenshot directly; Mistral first sends it to Mistral OCR and then sends both the original image and OCR text to the selected Mistral chat model. Optional **Pix2Text (local, experimental)** OCR runs locally, then sends the original image plus its OCR text to the selected Gemini/Mistral solver; it skips Mistral's separate OCR API call.
- The optional portable config stores provider-specific API keys, model names, and the OCR selection in `screen_answer_config.json` beside the app. It is **plain text**; keep it private and never upload or share it. The old Gemini-only config format is migrated automatically. The sidecar is not included in releases.
- Use only with screen content you are permitted to share with the selected provider, and where AI assistance is allowed. AI answers can be wrong; the tray color is a suggestion, not a guarantee.
- There is no self-destruct or file-deletion hotkey. **Ctrl+Alt+Q** and the tray menu's **Exit** command close the app normally.

## Use

1. Run `answer_tray.py`, the packaged `ScreenAnswer.exe`, or the experimental `ScreenAnswer-Pix2Text.exe`. A grey tray icon appears; Windows may place it in the tray overflow/hidden-icons menu.
2. Double-click the tray icon to open Settings. Choose **Google Gemini** or **Mistral**, select an OCR backend, enter that provider's API key, acknowledge the matching upload notice, and click **Save settings**. **Provider default** preserves existing behavior; **Pix2Text (local, experimental)** is available when running from source with its optional package installed. The experimental Pix2Text EXE selects local Pix2Text OCR by default. The defaults are `gemini-3.8-flash` for Gemini and `mistral-medium-latest` for Mistral; the model names can be changed. The Mistral model uses high reasoning effort when supported. Existing configs using the previous default `ministral-14b-2512` are upgraded to `mistral-medium-latest`; other custom model names are retained. Create a separate Mistral key in [Mistral Studio](https://console.mistral.ai/).
3. Press **Ctrl+Alt+S** or click **Capture & ask now**. The tray icon reports the returned option:
   - Red: option 1
   - Yellow: option 2
   - Green: option 3
   - Blue: option 4
   - Grey: ready / no reliable answer / request failed
4. A result stays at full color for 10 seconds, then fades to grey over about 1.5 seconds. **Ctrl+Alt+Q** exits.

Leave the portable-config checkbox clear to keep settings in memory for that run only, or check it to store keys/models beside the app. If enabled, the sidecar can retain settings for **both** providers. Copy the EXE and sidecar together to another device. A browser login is not needed to use an already-created API key, but the device needs internet access and the selected account's model access/usage limits must permit requests. With **Provider default** OCR, the Mistral flow makes a separate OCR API call before chat; OCR may have separate charges or access requirements. If that OCR is unavailable, the app logs it in Diagnostic mode and falls back to sending the original screenshot to Mistral chat. Transient Mistral HTTP 429 responses are retried up to the app's bounded limit, honoring a short `Retry-After` header when provided; persistent rate limits or exhausted monthly quotas still require waiting or checking the Studio usage limits.

When **Pix2Text (local, experimental)** is selected, the app runs OCR on-device and skips Mistral's OCR API request. The screenshot and OCR transcript are still sent to the selected AI solver, so this is not fully offline and does not bypass that provider's chat quota. The [experimental `ScreenAnswer-Pix2Text.exe` release](https://github.com/Exo2v/Repository-for-answering-machine/releases/download/v1.3.0-experimental/ScreenAnswer-Pix2Text.exe) is a separate 64-bit Windows 10+ standalone build that bundles Pix2Text and its Python dependencies, but not model weights. The current download is about 543 MB; its first OCR use downloads model files to the user profile, so it needs internet access and extra disk space. The standard 32-bit EXEs remain the Windows 7-compatible/provider-default versions. If local OCR fails or returns no text, the app continues with the original screenshot and provider vision.

API model names, availability, free access, quotas, and pricing can change; check the selected provider's account and documentation for current terms.

## Diagnostic test build

`ScreenAnswer-Diagnostic.exe` opens a live diagnostics window at startup. It shows startup/configuration state, hotkey registration, capture size and timing, provider-specific HTTP attempts/statuses/retries and available rate-limit headers, API error details, response metadata, answer parsing, and the final tray result. For Mistral it shows the OCR API's first-page Markdown transcription when provider-default OCR is selected, or Pix2Text's local Markdown when local OCR is selected, along with the solver's final user-facing response; for Gemini it shows Pix2Text's local Markdown when enabled and the final model response. The Mistral API's separate internal reasoning chunks are not displayed.

This is the real app, **not a simulation**. After consent and an explicit capture action, it uploads the full desktop screenshot to the selected provider. Diagnostic logs omit API keys and screenshot pixels, but may contain text read from the entire screen and the model's final answer/solution. Review the log before copying, saving, or sharing it. Screenshots and logs are not automatically saved to disk; only save/export a log if you want to keep it.

The diagnostics window opens automatically in the test build; right-click its tray icon and choose **Show diagnostics** to reopen it. Use **Open settings** there to choose a provider and configure its key. If using a portable config, keep the diagnostic EXE beside `screen_answer_config.json`.

From source, run `python answer_tray.py --diagnostics`. The experimental `ScreenAnswer-Pix2Text.exe` also accepts `--diagnostics` to open the diagnostics window; the separate `ScreenAnswer-Diagnostic.exe` is for the standard build.

## Run from source

- **Windows 10:** Python 3.8 or later with Tcl/Tk included.
- **Windows 7:** Python 3.8.10 (the last Python release supporting Windows 7), on Windows 7 SP1 with current system updates. Select Tcl/Tk in the official Python installer.

Launch without a console window:

```powershell
pythonw answer_tray.py
```

Use `python answer_tray.py` if you want a console. The default/provider-default mode uses only the Python standard library; Pix2Text is optional. Platform-independent unit tests can be run with:

```powershell
python -m unittest discover -s tests -v
```

## Optional Pix2Text local OCR (experimental)

Pix2Text is an open-source OCR toolkit that extracts text and mathematical formulas into Markdown/LaTeX; it does **not** solve the question. This app uses it only as a local OCR aid, then sends the original screenshot and transcript to the selected Gemini/Mistral solver. In this mode, Mistral's separate OCR API call is skipped, but its chat request still requires an available Mistral quota. The app keeps the screenshot in memory and asks Pix2Text not to save intermediate/debug images.

To try it from source, install the optional dependency in the same Python environment used to launch the app:

```powershell
python -m pip install -r requirements-pix2text.txt
python answer_tray.py
```

Open Settings, choose **Pix2Text (local, experimental)**, acknowledge the updated upload notice, then save and capture. On first use, Pix2Text may download model files to the user profile and take several minutes. Later runs reuse its local model cache. The installed Pix2Text release supports text/formula recognition through its Python API; see the [official repository](https://github.com/breezedeus/Pix2Text) and [usage guide](https://pix2text.readthedocs.io/zh-cn/stable/usage/).

This optional dependency stack is much larger than Screen Answer and is not included in the 32-bit Windows 7/10 standard EXEs. The experimental `ScreenAnswer-Pix2Text.exe` bundles the Python/OCR runtime for 64-bit Windows 10+, while downloading model weights on first use. To build a custom Pix2Text-enabled executable, use a compatible 64-bit Python environment and the packaging steps in the GitHub workflow. If Pix2Text fails or returns no text, the app falls back to sending the original screenshot to the AI solver without OCR text. Verify transcription and answers; this experimental mode does not guarantee higher JEE accuracy.

## Build standalone Windows executables

PyInstaller is needed only on the build machine:

```powershell
python -m pip install pyinstaller==5.13.2
pyinstaller --noconfirm --onefile --windowed --name ScreenAnswer answer_tray.py
pyinstaller --noconfirm --onefile --windowed --name ScreenAnswer-Diagnostic answer_tray.py
```

The results are `dist/ScreenAnswer.exe` and `dist/ScreenAnswer-Diagnostic.exe`. For the best chance of Windows 7 compatibility, build with 32-bit Python 3.8.10 and test on Windows 7 SP1.

The GitHub Actions workflow in `.github/workflows/windows-release.yml` builds the standard 32-bit executables on each branch update. On a version tag, it additionally builds and attaches the experimental x64 `ScreenAnswer-Pix2Text.exe`, which includes its Python/OCR dependencies but downloads model weights on first use. That build targets Windows 10+ x64; the standard executables remain the Windows 7-compatible option.
