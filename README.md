# Screen Answer

A small, user-triggered Windows study helper. The default app uses Python's standard library (including Tkinter from the official Python installer) and Windows APIs through `ctypes`; no `pip` runtime dependencies are required. The experimental Pix2Text build bundles its Python runtime and OCR dependencies, but downloads model weights on first use. For a project-wide overview covering the standard app, Lasso variants, OCR, diagnostics, configuration, privacy, testing, builds, and releases, see the [project guide](docs/project-guide.md). For the v1.6.0 APInex/Ollama request flow and release-specific implementation detail, see the [detailed implementation guide](docs/v1.6.0-apinex-ollama-implementation-guide.md).

## Privacy and behavior

- The app has a **visible notification-area (system tray) icon**. It does not hide itself or install itself at Windows startup. Release files contain no API keys or configured sidecar; on first run, hosted-key fields are blank unless the user configured an environment variable, and screenshot consent is off.
- A screenshot is captured only after **Ctrl+Alt+S**, **Capture & ask now**, or the tray menu's **Capture and ask** action.
- Each capture includes the **entire virtual desktop / all monitors**. The PNG is kept in memory and routed either over HTTPS to the selected hosted provider or over loopback to the local Ollama server. It is not written to a screenshot file.
- Choose **APInex**, **Google Gemini (direct)**, **Ollama (local)**, **Mistral**, or **OpenRouter** in standard Settings. Groq remains removed. **Live web search and tool execution are disabled.** Direct Gemini uses Google's `generateContent` API at `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`, with `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) or a key entered in Settings; it defaults to `gemini-3.8-flash`. These are direct Google model IDs, not APInex aliases, and Google's quota, billing and data terms apply. APInex uses `APINEX_API_KEY`; `MISTRAL_API_KEY` and `OPENROUTER_API_KEY` are also supported. APInex accepts only the curated free vision IDs `free/gemini-3.8-flash`, `free/gemini-3.1-pro`, and `free/gpt-6-luna`; the default remains `free/gemini-3.8-flash`, and the GPT-6 Luna ID is an alternative, not the default. These are APInex model aliases, not direct Google/OpenAI API integrations. No paid model fallback is allowed. APInex is a hosted intermediary and forwards requests to its model provider; review its data terms and quota before sending sensitive content. Ollama requires no key and sends the screenshot to `http://127.0.0.1:11434/api/chat` on this device; the default local model is `qwen3-vl:8b` and must be installed separately. Mistral uses its OCR endpoint before chat by default. OpenRouter still accepts only the two configured Gemma `:free` vision models and does not fall back to paid models. The optional **Pix2Text (local, experimental)** OCR runs locally and passes its transcript with the original image to the selected solver.
- The optional portable config stores supported provider keys, model names, and OCR selection in `screen_answer_config.json` beside the app. It is **plain text**; keep it private and never upload or share it. Gemini keys are accepted only under the explicit `gemini` provider entry and are never reused as APInex credentials; unknown legacy Google aliases and Groq settings are removed during migration. The sidecar is not included in releases.
- Use only with screen content you are permitted to share with the selected provider, and where AI assistance is allowed. AI answers can be wrong; the tray color is a suggestion, not a guarantee.
- The standard Screen Answer variants have no self-destruct or file-deletion hotkey. **Ctrl+Alt+Q** and the tray menu's **Exit** command close those apps normally.

## Use

1. Download `ScreenAnswer.exe` or `ScreenAnswer-Diagnostic.exe` from the [v1.7.0-experimental release](https://github.com/Exo2v/indigo-otter-731/releases/tag/v1.7.0-experimental), or run `answer_tray.py` / the optional `ScreenAnswer-Pix2Text.exe`. A grey tray icon appears; Windows may place it in the tray overflow/hidden-icons menu. The diagnostic EXE opens its live log at startup. The standard EXEs do not bundle Pix2Text; provider choices are in Settings.
2. Double-click the tray icon to open Settings. Choose **APInex**, **Google Gemini**, **Ollama (local)**, **Mistral**, or **OpenRouter**, select the OCR backend, enter a key only for hosted providers, acknowledge the matching data-path notice, and click **Save settings**. The default provider remains APInex with `free/gemini-3.8-flash`; this is an APInex model alias. For direct Google API calls, select **Google Gemini**, use a Google AI Studio key, and keep its model ID (default `gemini-3.8-flash`) distinct from APInex's `free/` alias. APInex permits only the curated free vision IDs `free/gemini-3.8-flash`, `free/gemini-3.1-pro`, and `free/gpt-6-luna`; the new GPT-6 Luna option does not replace the default and receives the same base64 screenshot chat-completions request. The APInex daily allowance, upstream provider, and data terms apply. APInex's [pricing page](https://apinex.bond/pricing) says free-category models include 1M tokens/day and lists `free/gpt-6-luna` as free, but its [live model catalog](https://apinex.bond/developers/models) shows a $0.75/1M price for the same ID. Treat this as unresolved: verify your account's quota and billing behavior before repeated use. The app does not select a paid model as fallback, but it cannot independently guarantee how APInex bills an account. For local inference, choose Ollama; it has no API-key field and defaults to `qwen3-vl:8b`. Install Ollama 0.12.7+ and run `ollama pull qwen3-vl:8b` first (the model download is about 6 GB; actual memory needs vary). Ollama requests go only to `127.0.0.1:11434`; choose an installed vision-capable model in Settings if you use a different one. Mistral's default flow uses hosted OCR before chat. OpenRouter accepts only `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`; both are explicit free variants. It requests medium reasoning and excludes internal reasoning from the returned text. Existing Mistral configs using `ministral-14b-2512` are upgraded to `mistral-medium-latest`; unsupported APInex/OpenRouter models are reset to safe defaults, while valid Ollama model names are retained. Create hosted API keys in [APInex](https://apinex.bond/developers/auth), [Google AI Studio](https://aistudio.google.com/apikey), [Mistral Studio](https://console.mistral.ai/), or [OpenRouter](https://openrouter.ai/keys). Ollama does not need an API key.
3. Press **Ctrl+Alt+S** or click **Capture & ask now**. The tray icon reports the returned option:
   - Red: option 1
   - Yellow: option 2
   - Green: option 3
   - Blue: option 4
   - Grey: ready / no reliable answer / request failed
4. A result stays at full color for 10 seconds, then fades to grey over about 1.5 seconds. **Ctrl+Alt+Q** exits.

Leave the portable-config checkbox clear to keep settings in memory for that run only, or check it to store settings beside the app. API keys for hosted services are plaintext in the optional sidecar; Ollama has no key. Copy the EXE and sidecar together only if you intentionally want portable settings. APInex, Google Gemini, Mistral, and OpenRouter require internet access and their account limits to permit requests. Ollama requires its local server and selected vision model to be installed/running on the same device; a missing model produces an `ollama pull <model>` hint. With **Provider default** OCR, the Mistral flow makes a separate OCR API call before chat; OCR may have separate charges or access requirements. Transient hosted API errors are retried within a bounded limit; persistent rate limits or exhausted quotas still require waiting or checking the provider's usage limits.

When **Pix2Text (local, experimental)** is selected, the app runs OCR on-device and skips Mistral's OCR API request. The screenshot and OCR transcript are still sent to the selected AI solver, so this is not fully offline and does not bypass that provider's chat quota. The [experimental `ScreenAnswer-Pix2Text.exe` release](https://github.com/Exo2v/indigo-otter-731/releases/download/v1.3.0-experimental/ScreenAnswer-Pix2Text.exe) is a separate 64-bit Windows 10+ standalone build that bundles Pix2Text and its Python dependencies, but not model weights. The current download is about 543 MB; its first OCR use downloads model files to the user profile, so it needs internet access and extra disk space. The standard 32-bit EXEs remain the Windows 7-compatible/provider-default versions. If local OCR fails or returns no text, the app continues with the original screenshot and provider vision.

## New Lasso family (APInex + OpenRouter; Windows 11 and Windows 7)

The new Lasso family is separate from `Lasso1`/`LassV7` and `LassoV2`/`LassV27`; those existing builds and their config folders are unchanged. Its workflow is configured to package `Lasso.exe` for 64-bit Windows 11 and `LassoWin7.exe` for 32-bit Windows 7 (Python 3.8.10), with configs at `%APPDATA%\Lasso\config.json` and `%APPDATA%\LassoWin7\config.json`. First-run API keys are blank and screenshot consent is off; no configured user files or credentials are bundled. The `lasso3` release job is configured, but the EXEs are not public until that release is published.

Lasso supports **APInex** and **OpenRouter** only; Groq is intentionally not included. APInex requests use `https://api.apinex.bond/v1/chat/completions`; OpenRouter requests use `https://openrouter.ai/api/v1/chat/completions`. Each capture normally sends one provider-formatted chat-completions request with the image; there is no separate OCR, search, or tool API call. Retryable 429/5xx errors can cause up to three HTTP attempts total, so retries may use additional request quota. Live web search and tool execution are disabled. Settings lets you choose the provider and enter that provider's own key, but model IDs are not shown or editable in the GUI: they remain in the config file. APInex starts with `free/gemini-3.8-flash`, with `free/gemini-3.1-pro` as an optional config-only ID; `free/gpt-6-luna` remains available only in standard Screen Answer, not this Lasso family. OpenRouter remains restricted to `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`; there is no paid or cross-provider fallback. APInex quotas and pricing can change, so verify your account's current terms before relying on any model.

If the selected provider key is missing, Settings opens automatically at startup so you can enter it; once a key is saved, Settings opens only on request. No diagnostic console opens at startup. **Save** closes Settings. **Ctrl+Alt+S** captures the full virtual desktop only after a key is configured and screenshot consent is explicitly saved. The tray menu and Settings button can open a separate **diagnostic console only on request**; its log can include OCR/model answer text and provider errors, but omits API keys and screenshot pixels. `LassoWin7.exe` has no app-generated tray balloons or hover tooltips; its icon color is the runtime status. **Ctrl+Alt+O** silently closes the running Lasso executable and schedules deletion of only that executable and its matching `config.json`; unexpected files are left untouched. The tray-menu self-destruct action still asks for confirmation.

API model names, availability, free access, quotas, and pricing can change; check the selected provider's account and documentation for current terms.

## Otterary version 1 (Gemini + OpenRouter; Windows 11 and Windows 7)

Otterary is a separate app family with two release builds: `Otterary.exe` for Windows 11 x64 and `OtteraryWin7.exe` for Windows 7 x86. The current no-retry build is [Otterary version 1.0.1](https://github.com/Exo2v/indigo-otter-731/releases/tag/otterary-v1.0.1). It supports direct Google Gemini and OpenRouter. On first launch Settings opens with API-key fields blank and screenshot-upload consent off. Enter provider credentials in the UI; no environment variables are required and no API keys are bundled. Settings and keys are stored in a private per-user config file as plain text. OpenRouter is restricted to its two configured vision-model IDs; Gemini's model ID is editable in Settings. Provider quota, data terms, and billing apply.

**Ctrl+Alt+S** captures the full desktop after saved upload consent and sends one provider request attempt; Otterary does not automatically retry failures. Pressing the hotkey again starts a new request. The tray icon reports the answer through color only: no hover tooltip and no tray balloons/notifications. Right-click the tray icon and choose **Open diagnostic console** to open it; it remains hidden otherwise. **Ctrl+Alt+O** silently closes Otterary and schedules deletion of only the running executable and matching config file. The right-click self-destruct action asks for confirmation. The `otterary` and versioned `otterary-v*` workflow tags publish both Windows executables together; see the [Otterary guide](docs/otterary.md) for setup, config paths, and tray behavior.

## LassoV2 / LassV27 build flow (OpenRouter-only; release pending)

The repository contains a workflow for tray-only, OpenRouter-only `LassoV2.exe` and a dedicated 32-bit `LassV27.exe` build for Windows 7, packaged with Python 3.8.10 and PyInstaller 5.13.2. CI can build and smoke-check both, but **as of 8 October 2026 there is no public `lasso2` tag/release**, so those release assets and the matching WebPull download URL are not yet available. Do not treat the `lasso2` download command below as live until the release is published. The standard Screen Answer release uses the APInex, local Ollama, Mistral, and OpenRouter provider set described above. Neither Lasso variant opens a GUI at startup: right-click the tray and choose **Open** to show Settings; **Save** writes the config and closes the Settings window. A small **Diagnostics** button opens the live diagnostic page only on demand; it is not shown automatically. **Ctrl+Alt+S** captures only after upload consent is enabled. Live web search and tool execution are disabled.

The legacy [Lasso1 / LassV7 release](https://github.com/Exo2v/indigo-otter-731/releases/tag/lasso1) remains available with its existing executables and release-published WebPull script. Its config paths remain `%APPDATA%\Lasso1\config.json` and `%APPDATA%\LassV7\config.json`; the prepared `lasso2` build flow does not overwrite any `lasso1` assets or redirect either legacy executable.

Each new executable has its own per-user config: `LassoV2.exe` uses `%APPDATA%\LassoV2\config.json`, while `LassV27.exe` uses `%APPDATA%\LassV27\config.json`. New configs are created at runtime with a blank API-key value and `google/gemma-4-31b-it:free` as the default OpenRouter model; no credential or config file is bundled. Screenshot-upload consent is off. The Settings GUI has no model field or model value—model selection is exclusively in the matching config file. Enter the API key and enable consent in Settings only if you agree to send screenshots through OpenRouter to its free-model host; the host's data terms apply, so do not upload sensitive screens. To change the model, right-click and choose the matching **Open ... config file** action, set `models.openrouter` to `google/gemma-4-31b-it:free` or `google/gemma-4-26b-a4b-it:free`, then restart the app. The Diagnostics page is opened manually from Settings or the tray menu; its in-memory log is not saved unless you choose Save, and may include the model's final text or provider error details. API keys and screenshot pixels are not logged; review any exported log before sharing it.

`LassV27.exe` (like legacy `LassV7.exe`) sends no Windows notification-area balloons and registers no tray hover tooltips. While it works, the tray icon's color is the only runtime feedback. **Ctrl+Alt+O** silently closes a Lasso build and schedules removal of only that running EXE and its matching `config.json`. The tray-menu self-destruct action still asks for confirmation. The config directory is removed only if empty; unexpected files are left alone. If cleanup cannot be scheduled, the app stays open.

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

Existing configs with a missing or blank model are filled with the free default at startup. Previously saved OpenRouter IDs outside the current free vision allowlist are replaced with the safe default; a Lasso model migration also clears old screenshot consent so the new route requires explicit re-consent. Valid free OpenRouter variants, API keys, and otherwise applicable consent are preserved. The LassoV2 and LassV27 executables use models from their separate per-user config files and do not show model settings in the GUI. These dedicated Lasso builds remain OpenRouter-only and are unaffected by the standard ScreenAnswer provider changes. Neither new Lasso executable reads credentials from the download folder.

Once the `lasso2` release is published, its WebPull command is intended to be:

```powershell
irm https://github.com/Exo2v/indigo-otter-731/releases/download/lasso2/webpull.ps1 | iex
```

That command is not available until the release/tag and `webpull.ps1` asset exist. The script is designed to create a `LassV27-WebPull` folder containing `LassV27.exe` and setup notes; if that folder already exists it creates a numbered sibling rather than overwriting files. It does not bundle credentials. The repository's existing `servomotor` file appears to contain an API credential, so it is intentionally excluded from release downloads. Revoke/rotate that credential; if `servomotor` is meant to be a non-secret file, provide a sanitized copy before it is added.

## Diagnostic test build

The `ScreenAnswer-Diagnostic.exe` test build opens a live diagnostics window at startup and includes APInex, direct Google Gemini, local Ollama, Mistral, and OpenRouter. It shows startup/configuration state, hotkey registration, capture size and timing, provider-specific HTTP attempts/statuses/retries and available rate-limit headers, API error details, response metadata, answer parsing, and the final tray result. For Mistral it shows the OCR API's first-page Markdown transcription when provider-default OCR is selected, or Pix2Text's local Markdown when local OCR is selected, along with the solver's final user-facing response. APInex, Gemini, Ollama, and OpenRouter show Pix2Text's local Markdown when enabled and the model's final response; Gemini logs token counts but filters model thought parts, while Ollama requests go to the local loopback service. Hidden reasoning fields are not displayed. Direct Google Gemini is included as a standard provider; Groq remains removed.

This is the real app, **not a simulation**. After consent and an explicit capture action, it uploads the full desktop screenshot to the selected provider. Diagnostic logs omit API keys and screenshot pixels, but may contain text read from the entire screen, the model's final answer/solution, and provider-supplied error details. Review the log before copying, saving, or sharing it. Screenshots and logs are not automatically saved to disk; only save/export a log if you want to keep it.

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

Pix2Text is an open-source OCR toolkit that extracts text and mathematical formulas into Markdown/LaTeX; it does **not** solve the question. This app uses it only as a local OCR aid, then sends the original screenshot and transcript to the selected APInex, direct Gemini, Ollama, Mistral, or OpenRouter solver. In this mode, Mistral's separate OCR API call is skipped, while APInex, Gemini, Ollama, and OpenRouter receive the screenshot through vision chat. The app keeps the screenshot in memory and asks Pix2Text not to save intermediate/debug images.

To try it from source, install the optional dependency in the same Python environment used to launch the app:

```powershell
python -m pip install -r requirements-pix2text.txt
python answer_tray.py
```

Open Settings, choose **Pix2Text (local, experimental)**, acknowledge the updated upload notice, then save and capture. On first use, Pix2Text may download model files to the user profile and take several minutes. Later runs reuse its local model cache. The installed Pix2Text release supports text/formula recognition through its Python API; see the [official repository](https://github.com/breezedeus/Pix2Text) and [usage guide](https://pix2text.readthedocs.io/zh-cn/stable/usage/).

This optional dependency stack is much larger than Screen Answer and is not included in the 32-bit Windows 7/10 standard EXEs. The experimental `ScreenAnswer-Pix2Text.exe` bundles the Python/OCR runtime for 64-bit Windows 10+, while downloading model weights on first use. To build a custom Pix2Text-enabled executable, use a compatible 64-bit Python environment and the packaging steps in the GitHub workflow. If Pix2Text fails or returns no text, the app falls back to sending the original screenshot to the selected solver (APInex, direct Gemini, Ollama, Mistral, or OpenRouter) without OCR text. Verify transcription and answers; this experimental mode does not guarantee higher JEE accuracy.

## Build standalone Windows executables

PyInstaller is needed only on the build machine:

```powershell
python -m pip install pyinstaller==5.13.2
pyinstaller --noconfirm --onefile --windowed --name ScreenAnswer answer_tray.py
pyinstaller --noconfirm --onefile --windowed --name ScreenAnswer-Diagnostic answer_tray.py
```

The results are `dist/ScreenAnswer.exe` and `dist/ScreenAnswer-Diagnostic.exe`. Both include APInex, local Ollama, Mistral, and OpenRouter; the diagnostic variant opens live logs at startup. For the best chance of Windows 7 compatibility, build with 32-bit Python 3.8.10 and test on Windows 7 SP1. The Ollama service itself must be installed and running locally; the Screen Answer EXE does not bundle it or any model weights.

The GitHub Actions workflow in `.github/workflows/windows-release.yml` builds and smoke-checks the two standard 32-bit executables on branch updates and attaches them to `v*` version-tag releases. The legacy `lasso1` tag builds the original `Lasso1.exe` / `LassV7.exe` pair. The `lasso2` tag is configured to build the OpenRouter-only `LassoV2.exe` and Windows 7-compatible `LassV27.exe` pair with the WebPull script; it does not add APInex or Ollama to those dedicated Lasso variants. No public `lasso2` tag/release was listed as of 8 October 2026. The new `lasso3` workflow uses separate jobs for `Lasso.exe` (Windows 11 x64) and `LassoWin7.exe` (Windows 7 x86); the `lasso3` tag publishes both executables together. That workflow is configured but has not been run or published from this worktree. The experimental x64 `ScreenAnswer-Pix2Text.exe` remains available in the [v1.3.0-experimental release](https://github.com/Exo2v/indigo-otter-731/releases/download/v1.3.0-experimental/ScreenAnswer-Pix2Text.exe); it bundles the Python/OCR dependencies but downloads model weights on first use. That build targets Windows 10+ x64; the standard executables remain the Windows 7-compatible option. The workflow's separate Pix2Text build can be run via manual dispatch or an opt-in commit message containing `[pix2text-build]`; standard builds do not rebuild the large OCR bundle.
