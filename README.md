# Screen Answer

A small, user-triggered Windows study helper. The default app uses Python's standard library (including Tkinter from the official Python installer) and Windows APIs through `ctypes`; no `pip` runtime dependencies are required. The experimental Pix2Text build bundles its Python runtime and OCR dependencies, but downloads model weights on first use.

## Privacy and behavior

- The app has a **visible notification-area (system tray) icon**. It does not hide itself or install itself at Windows startup.
- A screenshot is captured only after **Ctrl+Alt+S**, **Capture & ask now**, or the tray menu's **Capture and ask** action.
- Each capture includes the **entire virtual desktop / all monitors**. The PNG is kept in memory and sent over HTTPS to the **selected provider**. It is not written to a screenshot file.
- Choose **Google Gemini**, **Mistral**, **Groq**, or **OpenRouter** in Settings. **Live web search and tool execution are not enabled.** Each provider needs its own API key. `GEMINI_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`, and `OPENROUTER_API_KEY` environment variables are supported. Gemini, Groq, and OpenRouter receive the screenshot directly through vision chat; none makes a separate OCR-service call. OpenRouter's `:online` model suffix is blocked to keep web search disabled. By default, Mistral first sends the screenshot to Mistral OCR, then sends both the original image and OCR text to its chat model. Optional **Pix2Text (local, experimental)** OCR runs locally, then sends the original image plus its OCR text to the selected solver; it skips Mistral's separate OCR API call.
- The optional portable config stores provider-specific API keys, model names, and the OCR selection in `screen_answer_config.json` beside the app. It is **plain text**; keep it private and never upload or share it. The old Gemini-only config format is migrated automatically. The sidecar is not included in releases.
- Use only with screen content you are permitted to share with the selected provider, and where AI assistance is allowed. AI answers can be wrong; the tray color is a suggestion, not a guarantee.
- The standard Screen Answer variants have no self-destruct or file-deletion hotkey. **Ctrl+Alt+Q** and the tray menu's **Exit** command close those apps normally.

## Use

1. Run `answer_tray.py`, the packaged `ScreenAnswer.exe`, the [updated `ScreenAnswer-Diagnostic.exe`](https://github.com/Exo2v/Repository-for-answering-machine/releases/download/v1.5.0-experimental/ScreenAnswer-Diagnostic.exe), the [dedicated `ScreenAnswer-Groq.exe`](https://github.com/Exo2v/Repository-for-answering-machine/releases/download/v1.5.0-experimental/ScreenAnswer-Groq.exe), or the experimental `ScreenAnswer-Pix2Text.exe`. A grey tray icon appears; Windows may place it in the tray overflow/hidden-icons menu. The diagnostic EXE opens its live log at startup and includes all four providers; the Groq EXE starts with Groq selected. Neither standard EXE bundles Pix2Text; all standard EXEs let you switch providers in Settings.
2. Double-click the tray icon to open Settings. Choose **Google Gemini**, **Mistral**, **Groq**, or **OpenRouter**, select an OCR backend, enter that provider's API key, acknowledge the matching upload notice, and click **Save settings**. **Provider default** preserves each provider's behavior: Gemini, Groq, and OpenRouter send the screenshot directly to vision chat; Mistral uses its OCR endpoint first. **Pix2Text (local, experimental)** is available when running from source with its optional package installed; the experimental Pix2Text EXE selects local OCR by default. The defaults are `gemini-3.8-flash` for Gemini, `mistral-medium-latest` for Mistral, `qwen/qwen3.8-27b` for Groq, and `google/gemini-3.8-flash` for OpenRouter; model names can be changed. OpenRouter model slugs are namespaced; select a vision-capable model, and do not append `:online` (web search is disabled). See [OpenRouter image-input documentation](https://openrouter.ai/docs/guides/overview/multimodal/image-understanding), [Groq's vision guide](https://console.groq.com/docs/vision), and the selected provider's catalog for availability and pricing. Existing configs using Mistral's previous default `ministral-14b-2512` are upgraded to `mistral-medium-latest`; other custom model names are retained. Create keys in [Google AI Studio](https://aistudio.google.com/apikey), [Mistral Studio](https://console.mistral.ai/), [GroqCloud](https://console.groq.com/keys), or [OpenRouter](https://openrouter.ai/keys).
3. Press **Ctrl+Alt+S** or click **Capture & ask now**. The tray icon reports the returned option:
   - Red: option 1
   - Yellow: option 2
   - Green: option 3
   - Blue: option 4
   - Grey: ready / no reliable answer / request failed
4. A result stays at full color for 10 seconds, then fades to grey over about 1.5 seconds. **Ctrl+Alt+Q** exits.

Leave the portable-config checkbox clear to keep settings in memory for that run only, or check it to store keys/models beside the app. If enabled, the sidecar can retain separate settings for **all four** providers. Copy the EXE and sidecar together to another device. A browser login is not needed to use an already-created API key, but the device needs internet access and the selected account's model access/usage limits must permit requests. With **Provider default** OCR, the Mistral flow makes a separate OCR API call before chat; OCR may have separate charges or access requirements. If that OCR is unavailable, the app logs it in Diagnostic mode and falls back to sending the original screenshot to Mistral chat. Transient Mistral HTTP 429 responses are retried up to the app's bounded limit, honoring a short `Retry-After` header when provided; persistent rate limits or exhausted monthly quotas still require waiting or checking the Studio usage limits.

When **Pix2Text (local, experimental)** is selected, the app runs OCR on-device and skips Mistral's OCR API request. The screenshot and OCR transcript are still sent to the selected AI solver, so this is not fully offline and does not bypass that provider's chat quota. The [experimental `ScreenAnswer-Pix2Text.exe` release](https://github.com/Exo2v/Repository-for-answering-machine/releases/download/v1.3.0-experimental/ScreenAnswer-Pix2Text.exe) is a separate 64-bit Windows 10+ standalone build that bundles Pix2Text and its Python dependencies, but not model weights. The current download is about 543 MB; its first OCR use downloads model files to the user profile, so it needs internet access and extra disk space. The standard 32-bit EXEs remain the Windows 7-compatible/provider-default versions. If local OCR fails or returns no text, the app continues with the original screenshot and provider vision.

API model names, availability, free access, quotas, and pricing can change; check the selected provider's account and documentation for current terms.

## Lasso1 Windows release (OpenRouter-only)

The separate [Lasso1 Windows release](https://github.com/Exo2v/Repository-for-answering-machine/releases/tag/lasso1) is a tray-only, OpenRouter-only variant; the standard Screen Answer releases above continue to include their existing providers. Lasso1 has no Settings or diagnostics windows. Its tray icon supports capture/exit actions, **Ctrl+Alt+S** captures, and the tray icon plus a colored Windows notification reports the answer. The default model is `google/gemini-3.8-flash`; no web-search plugin or tool execution is enabled.

On first launch, Lasso1 creates `%APPDATA%\Lasso1\config.json`. Open that file in a text editor, paste a newly created OpenRouter key into the empty `api_keys.openrouter` value, save, and restart Lasso1. The key is read from this per-user config file only; it is not embedded in the EXE and Lasso1 does not read an API key from an environment variable. The JSON file is plain text, so keep it private and do not upload or share it.

Right-click Lasso1's tray icon and choose **Open Lasso1 config folder** to open `%APPDATA%\Lasso1`. The same menu includes **Self-destruct Lasso1…**. This displays a confirmation warning, then closes the app and schedules deletion of `Lasso1.exe` and `config.json`. The folder is removed only if it is empty; other files are left untouched. If cleanup cannot be scheduled, Lasso1 stays open and deletes nothing.

Screenshot upload is **off by default**. Lasso1 captures and sends the full virtual desktop/all monitors to OpenRouter only when the config explicitly contains `"allow_screenshot_uploads": true`. This is your opt-in to sending screenshot contents to the provider; review what is on screen and confirm that sharing it is permitted before changing the setting. For example, the first-run config includes:

```json
{
  "provider": "openrouter",
  "api_keys": {
    "openrouter": ""
  },
  "models": {
    "openrouter": "google/gemini-3.8-flash"
  },
  "allow_screenshot_uploads": false
}
```

Set the key and, only after consenting, set the boolean to `true`; then restart the app for changes to take effect. When a key or consent is missing, capture is blocked and a tray notification points to the config file. The `lasso1` tag's Windows workflow builds and smoke-tests `Lasso1.exe` before publishing that separate release.

## Diagnostic test build

The [updated `ScreenAnswer-Diagnostic.exe`](https://github.com/Exo2v/Repository-for-answering-machine/releases/download/v1.5.0-experimental/ScreenAnswer-Diagnostic.exe) opens a live diagnostics window at startup and includes OpenRouter alongside Gemini, Mistral, and Groq. It shows startup/configuration state, hotkey registration, capture size and timing, provider-specific HTTP attempts/statuses/retries and available rate-limit headers, API error details, response metadata, answer parsing, and the final tray result. For Mistral it shows the OCR API's first-page Markdown transcription when provider-default OCR is selected, or Pix2Text's local Markdown when local OCR is selected, along with the solver's final user-facing response; for Gemini, Groq, and OpenRouter it shows Pix2Text's local Markdown when enabled and the final model response. OpenRouter sends the screenshot directly to its vision chat endpoint and does not call a separate OCR endpoint or enable live search. Hidden reasoning fields are not displayed.

This is the real app, **not a simulation**. After consent and an explicit capture action, it uploads the full desktop screenshot to the selected provider. Diagnostic logs omit API keys and screenshot pixels, but may contain text read from the entire screen, the model's final answer/solution, and provider-supplied error details. Review the log before copying, saving, or sharing it. Screenshots and logs are not automatically saved to disk; only save/export a log if you want to keep it.

The diagnostics window opens automatically in the test build; right-click its tray icon and choose **Show diagnostics** to reopen it. Use **Open settings** there to choose a provider and configure its key. If using a portable config, keep the diagnostic EXE beside `screen_answer_config.json`.

From source, run `python answer_tray.py --diagnostics`. The experimental `ScreenAnswer-Pix2Text.exe` and `ScreenAnswer-Groq.exe` also accept `--diagnostics` to open the diagnostics window; the separate `ScreenAnswer-Diagnostic.exe` is for the standard build.

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

Pix2Text is an open-source OCR toolkit that extracts text and mathematical formulas into Markdown/LaTeX; it does **not** solve the question. This app uses it only as a local OCR aid, then sends the original screenshot and transcript to the selected Gemini, Mistral, Groq, or OpenRouter solver. In this mode, Mistral's separate OCR API call is skipped, while Gemini, Groq, and OpenRouter still receive the screenshot through vision chat. The app keeps the screenshot in memory and asks Pix2Text not to save intermediate/debug images.

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
pyinstaller --noconfirm --onefile --windowed --name ScreenAnswer-Groq answer_tray.py
```

The results are `dist/ScreenAnswer.exe`, `dist/ScreenAnswer-Diagnostic.exe`, and `dist/ScreenAnswer-Groq.exe`. The diagnostic variant opens live logs at startup; all standard variants support OpenRouter. The Groq variant starts with Groq selected and does not bundle Pix2Text or call a separate OCR service; it sends the image directly to Groq's vision chat API. For the best chance of Windows 7 compatibility, build with 32-bit Python 3.8.10 and test on Windows 7 SP1.

The GitHub Actions workflow in `.github/workflows/windows-release.yml` builds all three standard 32-bit executables on each branch update and attaches them to `v*` version-tag releases. A separate `lasso1` tag builds, tests, smoke-checks, and publishes only `Lasso1.exe`; it does not attach the standard provider executables to that release. The updated diagnostic EXE is packaged and release-ready alongside the standard app and Groq variant. OpenRouter is a selectable provider in all standard builds; it sends screenshots directly to vision chat without Pix2Text or a hosted OCR call. The experimental x64 `ScreenAnswer-Pix2Text.exe` remains available in the [v1.3.0-experimental release](https://github.com/Exo2v/Repository-for-answering-machine/releases/download/v1.3.0-experimental/ScreenAnswer-Pix2Text.exe); it bundles the Python/OCR dependencies but downloads model weights on first use. That build targets Windows 10+ x64; the standard executables remain the Windows 7-compatible option. The workflow's separate Pix2Text build can be run via manual dispatch or an opt-in commit message containing `[pix2text-build]`; normal Groq/standard releases do not rebuild the large OCR bundle.
