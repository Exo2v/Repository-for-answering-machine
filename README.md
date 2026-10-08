# Screen Answer

A small, user-triggered Windows study helper. The default app uses Python's standard library (including Tkinter from the official Python installer) and Windows APIs through `ctypes`; no `pip` runtime dependencies are required. The experimental Pix2Text build bundles its Python runtime and OCR dependencies, but downloads model weights on first use.

## Privacy and behavior

- The app has a **visible notification-area (system tray) icon**. It does not hide itself or install itself at Windows startup.
- A screenshot is captured only after **Ctrl+Alt+S**, **Capture & ask now**, or the tray menu's **Capture and ask** action.
- Each capture includes the **entire virtual desktop / all monitors**. The PNG is kept in memory and sent over HTTPS to the **selected provider**. It is not written to a screenshot file.
- Choose **Google Gemini**, **Mistral**, **Groq**, or **OpenRouter** in Settings. **Live web search and tool execution are not enabled.** Each provider needs its own API key. `GEMINI_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`, and `OPENROUTER_API_KEY` environment variables are supported. Gemini, Groq, and OpenRouter receive the screenshot directly through vision chat; none makes a separate OCR-service call. Groq and OpenRouter model requests are fail-closed to a short allowlist of screenshot-capable reasoning models offered on free tiers; OpenRouter accepts explicit `:free` variants only. Neither provider falls back to a paid model; if an allowed endpoint is unavailable or over quota, the request fails after bounded same-model retries. Groq account plan and quota determine whether its allowlisted model is actually free for that account. OpenRouter sends the image through to the model host; host-specific data terms apply, so do not upload sensitive screens. By default, Mistral first sends the screenshot to Mistral OCR, then sends both the original image and OCR text to its chat model. Optional **Pix2Text (local, experimental)** OCR runs locally, then sends the original image plus its OCR text to the selected solver; it skips Mistral's separate OCR API call.
- The optional portable config stores provider-specific API keys, model names, and the OCR selection in `screen_answer_config.json` beside the app. It is **plain text**; keep it private and never upload or share it. The old Gemini-only config format is migrated automatically. The sidecar is not included in releases.
- Use only with screen content you are permitted to share with the selected provider, and where AI assistance is allowed. AI answers can be wrong; the tray color is a suggestion, not a guarantee.
- The standard Screen Answer variants have no self-destruct or file-deletion hotkey. **Ctrl+Alt+Q** and the tray menu's **Exit** command close those apps normally.

## Use

1. Run `answer_tray.py`, the packaged `ScreenAnswer.exe`, the [updated `ScreenAnswer-Diagnostic.exe`](https://github.com/Exo2v/indigo-otter-731/releases/download/v1.5.0-experimental/ScreenAnswer-Diagnostic.exe), the [dedicated `ScreenAnswer-Groq.exe`](https://github.com/Exo2v/indigo-otter-731/releases/download/v1.5.0-experimental/ScreenAnswer-Groq.exe), or the experimental `ScreenAnswer-Pix2Text.exe`. A grey tray icon appears; Windows may place it in the tray overflow/hidden-icons menu. The diagnostic EXE opens its live log at startup and includes all four providers; the Groq EXE starts with Groq selected. Neither standard EXE bundles Pix2Text; all standard EXEs let you switch providers in Settings.
2. Double-click the tray icon to open Settings. Choose **Google Gemini**, **Mistral**, **Groq**, or **OpenRouter**, select an OCR backend, enter that provider's API key, acknowledge the matching upload notice, and click **Save settings**. **Provider default** preserves each provider's behavior: Gemini, Groq, and OpenRouter send the screenshot directly to vision chat; Mistral uses its OCR endpoint first. **Pix2Text (local, experimental)** is available when running from source with its optional package installed; the experimental Pix2Text EXE selects local OCR by default. The defaults are `gemini-3.8-flash` for Gemini, `mistral-medium-latest` for Mistral, `qwen/qwen3.8-27b` for Groq, and `google/gemma-4-31b-it:free` for OpenRouter. Gemini and Mistral model names remain user-selectable. Groq is locked to its allowlisted vision/reasoning model. OpenRouter accepts only `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`; both are explicit zero-price variants that support image input and reasoning; the app requests medium reasoning while excluding internal reasoning from the returned text. No paid-model fallback is made. The Groq Qwen model is documented for vision and reasoning by [Groq's vision guide](https://console.groq.com/docs/vision) and [reasoning guide](https://console.groq.com/docs/reasoning); Groq accounts on its paid Developer plan may be billed for the same model, because billing is controlled by the account plan. See [OpenRouter's free-variant guide](https://openrouter.ai/docs/guides/routing/model-variants/free), its [reasoning controls](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens), and the [Gemma 4 31B free model page](https://openrouter.ai/google/gemma-4-31b-it:free) and [26B A4B free model page](https://openrouter.ai/google/gemma-4-26b-a4b-it:free) for current limits, image input, reasoning, and availability. Existing configs using Mistral's previous default `ministral-14b-2512` are upgraded to `mistral-medium-latest`; unsupported Groq/OpenRouter model entries are replaced with their safe defaults, while custom Gemini/Mistral models are retained. Create keys in [Google AI Studio](https://aistudio.google.com/apikey), [Mistral Studio](https://console.mistral.ai/), [GroqCloud](https://console.groq.com/keys), or [OpenRouter](https://openrouter.ai/keys).
3. Press **Ctrl+Alt+S** or click **Capture & ask now**. The tray icon reports the returned option:
   - Red: option 1
   - Yellow: option 2
   - Green: option 3
   - Blue: option 4
   - Grey: ready / no reliable answer / request failed
4. A result stays at full color for 10 seconds, then fades to grey over about 1.5 seconds. **Ctrl+Alt+Q** exits.

Leave the portable-config checkbox clear to keep settings in memory for that run only, or check it to store keys/models beside the app. If enabled, the sidecar can retain separate settings for **all four** providers. Copy the EXE and sidecar together to another device. A browser login is not needed to use an already-created API key, but the device needs internet access and the selected account's model access/usage limits must permit requests. With **Provider default** OCR, the Mistral flow makes a separate OCR API call before chat; OCR may have separate charges or access requirements. If that OCR is unavailable, the app logs it in Diagnostic mode and falls back to sending the original screenshot to Mistral chat. Transient Mistral HTTP 429 responses are retried up to the app's bounded limit, honoring a short `Retry-After` header when provided; persistent rate limits or exhausted monthly quotas still require waiting or checking the Studio usage limits.

When **Pix2Text (local, experimental)** is selected, the app runs OCR on-device and skips Mistral's OCR API request. The screenshot and OCR transcript are still sent to the selected AI solver, so this is not fully offline and does not bypass that provider's chat quota. The [experimental `ScreenAnswer-Pix2Text.exe` release](https://github.com/Exo2v/indigo-otter-731/releases/download/v1.3.0-experimental/ScreenAnswer-Pix2Text.exe) is a separate 64-bit Windows 10+ standalone build that bundles Pix2Text and its Python dependencies, but not model weights. The current download is about 543 MB; its first OCR use downloads model files to the user profile, so it needs internet access and extra disk space. The standard 32-bit EXEs remain the Windows 7-compatible/provider-default versions. If local OCR fails or returns no text, the app continues with the original screenshot and provider vision.

API model names, availability, free access, quotas, and pricing can change; check the selected provider's account and documentation for current terms.

## Lasso1 Windows release (OpenRouter-only)

The separate [Lasso1 Windows release](https://github.com/Exo2v/indigo-otter-731/releases/tag/lasso1) is tray-only and OpenRouter-only; the standard Screen Answer releases above keep their existing providers. It includes `Lasso1.exe` and a dedicated 32-bit `LassV7.exe` build for Windows 7, packaged with Python 3.8.10 and PyInstaller 5.13.2. CI builds and smoke-checks both. Neither opens a GUI at startup: right-click the tray and choose **Open** to show Settings; **Save** writes the config and closes the Settings window. A small **Diagnostics** button opens the live diagnostic page only on demand; it is not shown automatically. **Ctrl+Alt+S** captures only after upload consent is enabled. Live web search and tool execution are disabled.

Each executable has its own per-user config: `Lasso1.exe` uses `%APPDATA%\Lasso1\config.json`, while `LassV7.exe` uses `%APPDATA%\LassV7\config.json`. New configs leave the API-key value blank and set `google/gemma-4-31b-it:free` as the default OpenRouter model; no credential or config file is bundled. Screenshot-upload consent is off. The Lasso Settings GUI has no model field or model value—model selection is exclusively in the matching config file. Enter the API key and enable consent in Settings only if you agree to send screenshots through OpenRouter to its free-model host; the host's data terms apply, so do not upload sensitive screens. To change the model, right-click and choose the matching **Open ... config file** action, set `models.openrouter` to one of the two allowlisted Gemma `:free` IDs, then restart the app. The Diagnostics page is opened manually from Settings or the tray menu; its in-memory log is not saved unless you choose Save, and may include the model's final text or provider error details. API keys and screenshot pixels are not logged; review any exported log before sharing it.

LassV7 sends no Windows notification-area balloons and does not register tray hover tooltips. While it works, the tray icon's color is the only runtime feedback. **Ctrl+Alt+O** silently closes either Lasso build and schedules removal of only that build's EXE and matching `config.json`. The tray-menu self-destruct action still asks for confirmation. The config directory is removed only if empty; unexpected files are left alone. If cleanup cannot be scheduled, the app stays open.

Screenshot upload is **off by default**. A fresh config looks like:

```json
{
  "provider": "openrouter",
  "api_keys": {
    "openrouter": ""
  },
  "models": {
    "openrouter": "google/gemma-4-31b-it:free"
  },
  "allow_screenshot_uploads": false
}
```

Existing configs with a missing or blank model are filled with the free default at startup. Previously saved Groq/OpenRouter IDs outside the current free vision allowlists are replaced with the safe default; a Lasso model migration also clears old screenshot consent so the new route requires explicit re-consent. Valid free OpenRouter variants, API keys, and otherwise applicable consent are preserved. Both Lasso executables use the model from their separate per-user config files and do not show model settings in the GUI. Gemini/Mistral model settings and behavior are unchanged. Neither Lasso executable reads credentials from the download folder.

To download LassV7 to a new folder under Downloads from PowerShell, run:

```powershell
irm https://github.com/Exo2v/indigo-otter-731/releases/download/lasso1/webpull.ps1 | iex
```

The WebPull creates a `LassV7-WebPull` folder containing `LassV7.exe` and setup notes; if that folder already exists it creates a numbered sibling rather than overwriting files. It does not bundle credentials. The repository's existing `servomotor` file appears to contain an API credential, so it is intentionally excluded from the download. Revoke/rotate that credential; if `servomotor` is meant to be a non-secret file, provide a sanitized copy before it is added.

## Diagnostic test build

The [updated `ScreenAnswer-Diagnostic.exe`](https://github.com/Exo2v/indigo-otter-731/releases/download/v1.5.0-experimental/ScreenAnswer-Diagnostic.exe) opens a live diagnostics window at startup and includes OpenRouter alongside Gemini, Mistral, and Groq. It shows startup/configuration state, hotkey registration, capture size and timing, provider-specific HTTP attempts/statuses/retries and available rate-limit headers, API error details, response metadata, answer parsing, and the final tray result. For Mistral it shows the OCR API's first-page Markdown transcription when provider-default OCR is selected, or Pix2Text's local Markdown when local OCR is selected, along with the solver's final user-facing response; for Gemini, Groq, and OpenRouter it shows Pix2Text's local Markdown when enabled and the final model response. OpenRouter sends the screenshot directly to its vision chat endpoint and does not call a separate OCR endpoint or enable live search. Hidden reasoning fields are not displayed.

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

The GitHub Actions workflow in `.github/workflows/windows-release.yml` builds all three standard 32-bit executables on each branch update and attaches them to `v*` version-tag releases. The separate `lasso1` tag builds and smoke-checks both `Lasso1.exe` and the 32-bit Windows 7-compatible `LassV7.exe`, then publishes both in the same Lasso1 release without attaching the standard provider executables. The updated diagnostic EXE is packaged and release-ready alongside the standard app and Groq variant. OpenRouter is a selectable provider in all standard builds; it sends screenshots directly to vision chat without Pix2Text or a hosted OCR call. The experimental x64 `ScreenAnswer-Pix2Text.exe` remains available in the [v1.3.0-experimental release](https://github.com/Exo2v/indigo-otter-731/releases/download/v1.3.0-experimental/ScreenAnswer-Pix2Text.exe); it bundles the Python/OCR dependencies but downloads model weights on first use. That build targets Windows 10+ x64; the standard executables remain the Windows 7-compatible option. The workflow's separate Pix2Text build can be run via manual dispatch or an opt-in commit message containing `[pix2text-build]`; normal Groq/standard releases do not rebuild the large OCR bundle.
