# Screen Answer — Whole-Project Guide

**Prepared:** 8 October 2026<br>
**Project:** Screen Answer (repository historically named `Repository-for-answering-machine`; GitHub resolves to `Exo2v/indigo-otter-731`)<br>
**Current standard release:** [v1.7.0-experimental](https://github.com/Exo2v/indigo-otter-731/releases/tag/v1.7.0-experimental)<br>
**Audience:** users, testers, maintainers, and anyone preparing a build or release.

> This document describes the project as a whole: the standard Screen Answer program, optional OCR, diagnostic builds, the separate Lasso family, settings and data flow, tests, CI, release assets, and current limitations. For a deeper request-by-request APInex/Ollama explanation, see the [v1.6.0 implementation guide](v1.6.0-apinex-ollama-implementation-guide.md).

## 1. What the project is

Screen Answer is a small, Windows-only notification-area application for asking a vision model about a multiple-choice problem shown on the desktop. It is written as a Python/Tkinter program, uses Windows APIs through `ctypes` for its tray icon, global hotkeys, and desktop capture, and can be packaged as standalone Windows executables.

The central interaction is deliberately user-triggered:

1. The app sits in the notification area with a visible tray icon.
2. The user explicitly starts a capture.
3. The app captures the entire virtual desktop, encodes it in memory, and sends it to the selected vision backend (or to local Ollama).
4. The model is asked to solve one four-choice question and return a labelled answer position.
5. The app maps a reliable position to a color. If the response is ambiguous or the request fails, it stays neutral rather than guessing.

The app is not a continuous screen recorder, browser extension, hosted backend, remote-control service, or general-purpose question-answering website. It does not automatically capture at startup. It does not enable live web search or model tool execution. The answer is a suggestion and can be wrong; use it only where AI assistance is permitted.

## 2. Why there are several providers and executable families

The project has evolved to accommodate two different use cases:

- **Standard Screen Answer:** a general Windows app where the user can choose among hosted providers and a local model. The v1.6.0 line introduced APInex as the default and Ollama for local inference; the v1.7.0 build adds `free/gpt-6-luna` as an optional APInex model while keeping the existing default. Mistral and OpenRouter remain available.
- **Lasso variants:** the existing Lasso1/LassV7 and LassoV2/LassV27 families remain OpenRouter-only and unchanged. A new Lasso family adds APInex plus OpenRouter, with model IDs kept only in per-user config, explicit upload consent, silent scoped cleanup, and on-demand diagnostics. Its Windows 11 and Windows 7 builds use separate names/config folders.
- **Optional Pix2Text build:** a much larger experimental 64-bit build that adds local OCR. OCR extracts text and formulas; it does not solve the problem. The solver still receives the screenshot and, depending on provider, its OCR transcript.
- **Diagnostic build:** the standard program with a live diagnostics window opened automatically, for detailed testing of captures, OCR, network requests, response parsing, and errors.

The direct Google Gemini and Groq integrations were removed from the standard v1.6.0 test version because they were not working for the user. This is a provider change, not a rule banning every Google-family model name: APInex's default catalog alias still contains `gemini`, and OpenRouter's approved models still contain `google/gemma`. Those requests go through APInex or OpenRouter, not Google's direct API. If all Google-family model IDs are prohibited, the model choices must be replaced explicitly.

## 3. Product/build families at a glance

| Family | Main executables | Providers | Settings and behavior | Distribution status |
| --- | --- | --- | --- | --- |
| Standard | `ScreenAnswer.exe` | APInex (default), Ollama (local), Mistral, OpenRouter | Provider/model/OCR controls in standard Settings; consent starts off for every run | Current `v1.7.0-experimental` release |
| Standard diagnostics | `ScreenAnswer-Diagnostic.exe` | Same standard provider set | Same app, but opens the live diagnostic window at startup | Included in `v1.7.0-experimental` |
| Optional local OCR | `ScreenAnswer-Pix2Text.exe` | Same solver set; Pix2Text OCR is selected by default in that named build | 64-bit Windows 10+ experimental package; large dependencies, model weights downloaded separately | Published in `v1.3.0-experimental`; source/workflow can build it again on demand |
| Legacy Lasso | `Lasso1.exe`, `LassV7.exe` | OpenRouter only | Per-user config; Settings opens only on demand; no model field in GUI; `LassV7` suppresses balloons/tooltips | Public `lasso1` release |
| LassoV2 family | `LassoV2.exe`, `LassV27.exe` | OpenRouter only | Per-user config; Settings opens only on demand; no model field in GUI; `LassV27` suppresses balloons/tooltips | Workflow and WebPull script exist; no `lasso2` release/tag was listed on GitHub as of 8 October 2026. Existing release scope remains unchanged. |
| New Lasso family | `Lasso.exe`, `LassoWin7.exe` | APInex and OpenRouter only | Provider choice and key in Settings; model IDs config-only; separate diagnostics console on request; silent `Ctrl+Alt+O` cleanup | Build and release jobs prepared; `lasso3` tag publishes both targets |

`LassV7`, `LassV27`, and `LassoWin7` identify 32-bit Python 3.8.10 Windows 7-compatible targets. The new `Lasso.exe` target is 64-bit Python 3.11 for Windows 11; the Pix2Text build is a separate 64-bit Windows 10+ package because of its heavier dependency stack. The existing Lasso1/LassoV2 release families are not overwritten.

### Project history and rationale

- **v1.0.0–v1.2.1:** early iterations of the standard Windows tray helper. Consult the individual release notes for precise changes; this guide does not infer undocumented feature-by-feature history.
- **v1.3.0-experimental:** added a separate Pix2Text executable, exploring local text/formula extraction without replacing the model-based solver.
- **v1.4.0-experimental and v1.5.0-experimental:** continued the standard experimental line. The v1.5.0 release included standard/diagnostic builds and a historical Groq executable.
- **v1.6.0-experimental:** replaced direct Google Gemini and Groq integrations in the standard test version with APInex and local Ollama, while keeping Mistral and OpenRouter as choices. This tests a hosted intermediary and an on-device alternative without changing the separate Lasso provider scope.
- **v1.7.0-experimental:** adds the optional APInex free-category vision ID `free/gpt-6-luna`; `free/gemini-3.8-flash` remains the default. The account-level allowance and billing behavior still need live confirmation.
- **Lasso releases/builds:** the legacy Lasso1/LassV7 and LassoV2/LassV27 families remain OpenRouter-only. The new Lasso family adds APInex and OpenRouter with config-only model IDs and Windows 11/Windows 7 builds; it does not overwrite the earlier families.

The overall reason for these branches is controlled experimentation: compare a small, explicit provider set, local OCR and inference options, response reliability, cost/quota behavior, and the privacy consequences of each route before expanding distribution. The project's latest release remains marked experimental for that reason.

## 4. Main interaction and application architecture

### 4.1 User experience

For the standard app:

- A gray tray icon indicates ready/neutral state. Windows may hide it in the tray overflow.
- Double-clicking or choosing the Settings menu item opens Settings; settings do not need to appear at startup.
- The user chooses provider and OCR backend, supplies a hosted-provider key if necessary, reviews the matching data-path notice, checks consent, and saves.
- **Save settings** hides the Settings window. Standard settings stay in memory unless the user explicitly enables the portable sidecar checkbox.
- **Ctrl+Alt+S** or the tray's Capture command initiates a capture. The app does not capture without an explicit user action and active upload consent.
- **Ctrl+Alt+Q** exits the standard app normally.

The standard diagnostic executable performs the same real capture/provider requests. It is not a mock or simulation; only its diagnostics window is automatically visible.

### 4.2 Internal flow

```text
Tray menu / Ctrl+Alt+S / Settings capture button
                      │
                      ▼
Check provider key requirement and saved upload consent
                      │
                      ▼
Capture full Windows virtual desktop to PNG in memory
                      │
           optional local Pix2Text OCR
                      │
                      ▼
Dispatch one selected backend (provider default varies)
       ┌─────────┬─────────┬─────────┬─────────────┐
       │ APInex  │ Ollama  │ Mistral │ OpenRouter  │
       └─────────┴─────────┴─────────┴─────────────┘
                      │
                      ▼
Parse an explicit ANSWER line; do not infer from arbitrary digits
                      │
                      ▼
Tray color for positions 1–4; neutral on no reliable result/error
```

`answer_tray.py` contains the program's core code rather than a multi-package server/client architecture. It defines provider/model policy, config migration, API request helpers, OCR helpers, the Windows tray thread, the Tkinter Settings/diagnostics windows, capture worker, result parser, and build smoke-check flags.

### 4.3 Desktop capture and answer mapping

- The capture covers the full virtual desktop/all monitors, including unrelated visible windows.
- Windows GDI APIs are used to copy the desktop into memory and encode a PNG; no screenshot file is written.
- The code limits the capture to 24,000,000 pixels and PNG size to 12 MiB. It does not crop the screen.
- The request runs in a background worker so the interface can continue processing tray events.
- The response parser expects exactly one single-answer four-choice question and a final explicit `ANSWER: 1`, `ANSWER: 2`, `ANSWER: 3`, `ANSWER: 4`, or `ANSWER: 0` line. Letter choices map A→1, B→2, C→3, D→4.
- Red means option 1, yellow option 2, green option 3, blue option 4. Neutral gray means ready, no reliable answer, or failure. A successful color is held for about 10 seconds then fades back over about 1.5 seconds.
- No answer is guaranteed. Multiple questions, multi-select, free-response, illegible content, or an inconsistent solution should end neutral rather than trigger an unsupported guess.

## 5. Provider/API overview

### Standard provider matrix

| Provider | App endpoint | Default model | Credential | Default image/OCR route |
| --- | --- | --- | --- | --- |
| APInex | `https://api.apinex.bond/v1/chat/completions` | `free/gemini-3.8-flash` | `APINEX_API_KEY` | Direct screenshot to APInex vision chat; no separate OCR request |
| Ollama | `http://127.0.0.1:11434/api/chat` | `qwen3-vl:8b` | None | Screenshot to local Ollama vision chat; no cloud API request from this app |
| Mistral | `https://api.mistral.ai/v1/chat/completions` and `https://api.mistral.ai/v1/ocr` | `mistral-medium-latest` | `MISTRAL_API_KEY` | Provider-default OCR request then chat; Pix2Text can replace hosted OCR |
| OpenRouter | `https://openrouter.ai/api/v1/chat/completions` | `google/gemma-4-31b-it:free` | `OPENROUTER_API_KEY` | Direct vision chat through OpenRouter; no separate OCR request |

APInex, Mistral, and OpenRouter are the only hosted providers with API-key support in standard Screen Answer; Ollama has no key. The exact model IDs and policies are enforced by code. There is no cross-provider failover.

Hosted requests make at most three attempts for retryable errors. Rate-limit handling uses the provider's `Retry-After` value when available but will not wait indefinitely; temporary server errors use short bounded backoff. Per-attempt timeouts are 120 seconds for APInex, 60 seconds for Mistral and OpenRouter, and 300 seconds for Ollama. The response-body limit is 2 MiB. Output token caps are 2,048 for APInex/Ollama and 4,096 for Mistral/OpenRouter. These are bounds, not promises about end-to-end completion time (Mistral can make separate OCR and chat requests).

### 5.1 APInex

APInex is the standard default. The app restricts it to three configured free-category vision IDs:

- `free/gemini-3.8-flash` (default)
- `free/gemini-3.1-pro`
- `free/gpt-6-luna` (added as an optional alternative in v1.7.0; it does not replace the default)

It sends an OpenAI-compatible chat-completions request with the PNG as an `image_url` base64 data URL, `temperature: 0`, `reasoning_effort: "medium"`, and a 2,048-token output cap. The request contains no tool/plugin declaration. The key is sent in an HTTP Bearer Authorization header and never embedded in the EXE.

The app handles authentication, account quota, payload-size, rate-limit, missing-model, and temporary-upstream errors with provider-specific messages. Transient hosted calls are bounded to three attempts where the response class is retryable. The release tests mocked the HTTP endpoint; they did not make an APInex inference call.

APInex publicly describes a 1-million-token daily allowance for free-category models and a 5-request/minute/IP rate limit. Its [pricing page](https://apinex.bond/pricing) marks `free/gpt-6-luna` free in APInex's price columns, while the [live developer model catalog](https://apinex.bond/developers/models) lists $0.75 per 1M tokens for that same ID. This conflict means the exact account-level allowance and post-quota billing behavior remain unverified. The app treats the ID as a curated free-category choice, not a guarantee of zero cost; check the account usage/balance before use. GPT-6 Luna's [model specification](https://developers.openai.com/api/docs/models/gpt-6-luna) lists text and image input, and APInex's [chat API documentation](https://apinex.bond/developers/models/chat) documents image content parts; this project has not tested live image inference through APInex.

### 5.2 Ollama

Ollama is a local-service option, not a hosted key provider. The app posts to the fixed loopback URL `127.0.0.1:11434` and supplies the PNG as base64 in the chat message's `images` list. It sends no Authorization header. The default `qwen3-vl:8b` must be downloaded separately:

```powershell
ollama pull qwen3-vl:8b
```

The model listing reviewed for this project requires Ollama 0.12.7 or later and is about 6 GB. Hardware requirements, load time, speed, and answer quality vary. The app does not bundle Ollama, weights, or a remote Ollama URL. If the local service is unreachable, the app asks the user to start it; a missing model error includes a `ollama pull <model>` hint. Custom model names can be syntax-validated, but the app cannot guarantee they exist or accept images before calling the service.

### 5.3 Mistral

Mistral is retained as an editable hosted provider. With **Provider default** OCR, the flow is:

```text
screenshot → Mistral OCR → first-page Markdown transcript
           → Mistral chat with original screenshot + transcript
```

If the OCR request fails, the app may continue with the original image in chat. When local Pix2Text is selected, the app skips the separate Mistral OCR endpoint but still sends the screenshot and OCR transcript to Mistral chat. Existing config values for the retired default `ministral-14b-2512` are upgraded to `mistral-medium-latest`.

### 5.4 OpenRouter

OpenRouter remains in both the standard app and dedicated Lasso builds. Standard app provider choices are restricted to two exact explicit `:free` IDs:

- `google/gemma-4-31b-it:free` (default)
- `google/gemma-4-26b-a4b-it:free`

Paid/unqualified/online-search IDs are rejected by validation; the app does not fall back to a paid model. The image is sent through OpenRouter to a selected model host, so host-specific data terms apply. These model IDs contain Google/Gemma names, but the request is made through OpenRouter rather than a direct Google API.

## 6. OCR and prompt behavior

### Provider default versus Pix2Text

- **Provider default:** APInex, Ollama, and OpenRouter receive a direct image+prompt request. Mistral performs a separate hosted OCR request before chat.
- **Pix2Text (local):** Pix2Text runs locally and produces text/formula Markdown. The model still receives the original screenshot along with a bounded, explicitly untrusted OCR transcript. Pix2Text is not an AI answer solver and is not a way to keep data private when the chosen solver is hosted.
- If local OCR errors or returns no text, the app continues with the screenshot and no OCR context when the solver supports vision.
- OCR context is capped at 48,000 characters. Diagnostic OCR excerpts are capped, but can include text seen on screen.

The shared system/user instructions ask for one four-choice question, careful transcription, a concise and checkable calculation, answer-position mapping, and a final labelled answer line. They treat screenshot/OCR content as untrusted question data and explicitly prohibit live web search/tools. The application also omits tool fields from provider request bodies; prompt wording is not the only safeguard.

### Pix2Text dependency and build

The ordinary standard EXEs do not include the Pix2Text Python stack. From source, the optional requirements are in `requirements-pix2text.txt`:

```powershell
python -m pip install -r requirements-pix2text.txt
python answer_tray.py
```

That file pins Pix2Text 1.1.7, constrains NumPy below 2, and keeps Transformers below 5. The experimental release build uses 64-bit Python 3.11, CPU-only PyTorch 2.5.1/torchvision 0.20.1, PyInstaller 6.22.3, and explicit collection of the OCR/runtime packages. It bundles Python dependencies, not downloaded model weights. First OCR use may download model files and take several minutes; this package is large and targets Windows 10+ x64.

## 7. Settings, credentials, and config files

### Standard Screen Answer

- The default provider is APInex. The standard Settings GUI has a provider menu, OCR menu, hosted API-key entry, model field, optional portable-config checkbox, data-path consent checkbox, capture/save/exit controls, and status text.
- Provider/model settings are user-selectable in the standard GUI. This is different from the dedicated Lasso GUI, which has no model field.
- The default standard configuration path is `screen_answer_config.json` beside the Python source or frozen executable. The file is only written when the user selects portable saving.
- With portable saving off, saved settings stay in memory for that run. If a portable sidecar exists and the user turns the option off when saving, the app removes that sidecar.
- The sidecar is plaintext. It can contain hosted provider keys and model names, so protect it like a password file. Do not put it in a public archive or release.
- Standard upload consent is session-only; every new run starts with consent off, even when a sidecar contains API keys/models.
- Environment key lookup supports `APINEX_API_KEY`, `MISTRAL_API_KEY`, and `OPENROUTER_API_KEY`. An environment key may prefill the masked Settings entry. Ollama always resolves to no key.

The loader filters retired/unknown provider fields, resets invalid APInex/OpenRouter model IDs to safe defaults, rejects malformed Ollama model strings, and does not reinterpret an old unscoped Google/Groq key as an APInex key. If it can write the sidecar, it removes retired Google/Groq settings. The config migrates the old Mistral model default as noted above. The sidecar path is ignored by `.gitignore` and is not included in release artifacts.

### Dedicated Lasso builds

Each Lasso executable has a separate per-user config; the new family does not read or overwrite keys/configs from the older families:

| Executable | Provider scope | Config path |
| --- | --- | --- |
| `Lasso1.exe` | OpenRouter only | `%APPDATA%\Lasso1\config.json` |
| `LassV7.exe` | OpenRouter only | `%APPDATA%\LassV7\config.json` |
| `LassoV2.exe` | OpenRouter only | `%APPDATA%\LassoV2\config.json` |
| `LassV27.exe` | OpenRouter only | `%APPDATA%\LassV27\config.json` |
| `Lasso.exe` | APInex or OpenRouter | `%APPDATA%\Lasso\config.json` |
| `LassoWin7.exe` | APInex or OpenRouter | `%APPDATA%\LassoWin7\config.json` |

The four existing Lasso1/LassV7/LassoV2/LassV27 packages remain OpenRouter-only, accepting only `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`. The new Lasso family accepts two config-only APInex vision IDs (`free/gemini-3.8-flash` and `free/gemini-3.1-pro`) and those same two OpenRouter free IDs. `free/gpt-6-luna` remains an optional APInex model in standard Screen Answer only; it is not accepted by the new Lasso family. APInex quotas/pricing can change; no model is guaranteed free or unlimited. No paid or cross-provider fallback is added.

New Lasso first-run config (both keys blank and upload consent off):

```json
{
  "provider": "apinex",
  "api_keys": {"apinex": "", "openrouter": ""},
  "models": {
    "apinex": "free/gemini-3.8-flash",
    "openrouter": "google/gemma-4-31b-it:free"
  },
  "allow_screenshot_uploads": false
}
```

Settings lets the user choose APInex or OpenRouter and enter that provider's key. Models are deliberately absent from the Settings GUI; change only `models.apinex` or `models.openrouter` in the matching config file, then restart. APInex requests use `https://api.apinex.bond/v1/chat/completions`; OpenRouter requests use `https://openrouter.ai/api/v1/chat/completions`. Each capture normally makes one provider request; retryable 429/5xx errors can trigger up to three HTTP attempts total. The retries are additional requests and may count toward provider limits. There is no separate OCR, web-search, or tool API call in this family. Lasso never reads API keys from environment variables. Config writes are atomic, and keys are plaintext, so protect each per-user file as a credential. Invalid/missing models migrate to safe defaults and clear consent when the route/model changes.

## 8. Consent, privacy, and logging

Consent describes the actual recipient. Changing the selected provider or OCR backend clears consent in the standard UI; saving the new selection is required before a later capture. The standard app never persists consent. Consent for all Lasso builds is stored in the matching per-user config and begins false. The new Lasso family also clears consent when the provider/model route changes; switching from APInex to OpenRouter requires explicit renewed consent. Full-screen upload notices should be read carefully; do not capture screens the user is not permitted to share.

Screenshots are not logged or automatically saved. API keys are not logged and are redacted from diagnostic events. Diagnostic output can nevertheless contain:

- OCR Markdown read from the screen,
- the model's final response (which may reproduce question/screen text),
- provider error details, request timing, response metadata, and available rate-limit headers.

Diagnostic logs are in memory until the user explicitly saves/copies them. Review them before sharing. Do not send API keys or screenshots to chat/support tickets. The app does not package user configs, model weights, API credentials, or the potentially sensitive `servomotor` file in Windows release assets.

## 9. Tray menu, diagnostics, and Lasso-specific lifecycle

The standard tray menu offers capture, Settings, diagnostics where enabled, and Exit. Global hotkeys are registered by a separate Windows message thread:

- `Ctrl+Alt+S` — capture the full desktop.
- `Ctrl+Alt+Q` — exit normally.
- `Ctrl+Alt+O` — only registered for dedicated Lasso builds; silently triggers scoped self-cleanup.

For the existing Lasso families, right-click **Open** reveals Settings on demand. The new APInex/OpenRouter family opens Settings at startup when the selected provider's API key is missing; after a key is saved, it stays on demand. Saving closes Settings in every Lasso build. The menu opens the matching config file/folder. Legacy Lasso builds keep their on-demand Diagnostics page. The new family does not expose that page: its Settings button and tray menu launch a separate Windows diagnostic console only when explicitly requested. Closing Lasso shuts down that child process. Its log may contain OCR/model text and provider errors, but omits API keys and screenshot pixels; review it before sharing. The tray-menu self-destruct action asks for confirmation, while `Ctrl+Alt+O` does not prompt or show an app notification. Cleanup targets only the running Lasso EXE and its matching config file; a directory is removed only if empty, and unexpected files are left alone. If cleanup cannot be scheduled, the app stays open.

`LassV7`, `LassV27`, and the new `LassoWin7` suppress app-generated notification-area balloons and hover tooltips; their icon color is the runtime feedback. `Lasso1`, `LassoV2`, and the new 64-bit `Lasso.exe` may show normal status notifications and tooltips. Standard builds retain their existing feedback.

## 10. Repository map

| Path | Role |
| --- | --- |
| `answer_tray.py` | Main application, provider adapters, Windows tray/hotkeys, Tkinter Settings/diagnostics, capture/OCR, config migration, parsing, build smoke checks |
| `tests/test_answer_tray.py` | `unittest` coverage for providers, config, consent, Lasso behavior, parsing, image encoding, OCR, cleanup, and diagnostic modes |
| `README.md` | Quick user guide, downloads, provider descriptions, Lasso and Pix2Text overview, source/build instructions |
| `docs/project-guide.md` | This project-wide user/maintainer guide |
| `docs/v1.6.0-apinex-ollama-implementation-guide.md` | Focused technical detail for v1.6 APInex/Ollama, request shapes, testing status, and pilot plan |
| `docs/free-model-research-action-plan.md` | APInex allowance/pricing research, local-gateway comparison, quota plan, and open validation questions |
| `.github/workflows/windows-release.yml` | Standard, legacy Lasso, new Lasso Win11/x64 and Win7/x86, and Pix2Text Windows build/release workflows |
| `requirements-pix2text.txt` | Optional OCR dependency constraints; not needed for standard runtime |
| `webpull-lasso1.ps1` | PowerShell downloader/readme generator for the legacy LassV7 package |
| `webpull.ps1` | PowerShell downloader/readme generator for the prepared LassV27 package |
| `.gitignore` | Excludes bytecode, build/dist outputs, specs, and `screen_answer_config.json` |

The default standard runtime uses the Python standard library and Tkinter; the Pix2Text stack is the only optional third-party runtime. The program is Windows-only even though many parsing/config/API tests can run on other platforms.

## 11. Test strategy and build-time checks

Run the platform-independent test suite with:

```powershell
python -m unittest discover -s tests -v
```

The v1.7.0 baseline had 68 tests; the current working-tree suite has 81. Provider tests mock `urllib.request.urlopen`; they inspect payloads, model allowlists, redaction, retries, local endpoint errors, OCR context, and answer parsing without using a real key or service. Tests also cover config migration, no-key Ollama Settings behavior, upload consent, Lasso config paths and UI behavior, the new APInex/OpenRouter Lasso family, on-demand diagnostic-console lifecycle, tray notification suppression, self-cleanup scope, PNG encoding, and Pix2Text API import/behavior. No live inference is performed.

The EXEs support build smoke-check flags:

- `--check-apinex-ollama` — checks standard defaults, provider registry, endpoints, valid default models, and keyless Ollama policy.
- `--check-openrouter-support` — checks OpenRouter provider/key/model/endpoint wiring.
- `--check-lasso1-build`, `--check-lassv7-build`, `--check-lassov2-build`, `--check-lassv27-build`, `--check-lasso-build`, `--check-lassowin7-build` — verify expected executable identity, provider scope, model policy, config folder, diagnostics mode, and Python version/bitness where applicable.
- `--check-pix2text` — smoke-tests that the bundled Pix2Text API imports; it does not download model weights or test recognition quality.
- `--diagnostics` — opens diagnostics when running from source (except dedicated Lasso builds, whose diagnostic page remains on-demand).

The v1.6.0 Windows release workflow and a subsequent branch build have previously completed successfully, verifying the supported CI Python/build path and packaging/smoke checks. Those runs did not perform live provider inference or measure answer accuracy. Check the Actions result for the current commit separately.

## 12. Build and release lifecycle

### Standard Windows packages

The standard release workflow runs on branch pushes and on `v*` tags. It uses Windows Server 2022, 32-bit Python 3.8.10, and PyInstaller 5.13.2, runs the tests, builds `ScreenAnswer.exe` and `ScreenAnswer-Diagnostic.exe`, and smoke-checks APInex/Ollama and OpenRouter. A `v*` tag then attaches the two EXEs to a prerelease/release according to the tag name. For the best chance of Windows 7 compatibility, the standard package uses 32-bit Python 3.8.10. The CI runner is Windows Server 2022, not Windows 7, so Windows 7 is a compatibility target rather than an OS version exercised by that workflow.

A local standard build can be made on Windows with a compatible Python/Tkinter environment:

```powershell
python -m pip install pyinstaller==5.13.2
pyinstaller --noconfirm --clean --onefile --windowed --name ScreenAnswer answer_tray.py
pyinstaller --noconfirm --clean --onefile --windowed --name ScreenAnswer-Diagnostic answer_tray.py
```

The output goes to `dist/`. For a Windows 7-targeted build, use 32-bit Python 3.8.10 and test on the target OS; these commands do not bundle Ollama, OCR weights, or user settings. Use the workflow's named Lasso commands/check flags rather than renaming a standard EXE, because the executable name selects Lasso identity and its per-user config path.

### Lasso packages

The workflow keeps the existing Lasso1/LassV7 and LassoV2/LassV27 build jobs intact. Each pair uses x86 Python 3.8.10 and PyInstaller 5.13.2, runs the test suite and build smoke checks, validates its PowerShell script, and uploads two EXEs plus a renamed `webpull.ps1` artifact. Tags `lasso1` and `lasso2` publish their respective releases; manual dispatch or matching commit-message markers (`[lasso1-build]`, `[lasso2-build]`) build the pairs.

The new `lasso3` family has two separate packaging jobs: `Lasso.exe` uses x64 Python 3.11 for the Windows 11 target, and `LassoWin7.exe` uses x86 Python 3.8.10 for the Windows 7 target. Both jobs run the unit suite and their executable-specific smoke check. A `lasso3` tag runs both jobs and the release job, which publishes both EXEs together; manual dispatch or `[lasso3-build]` builds them as artifacts without publishing a release. The Windows CI runner is Windows Server 2022, so the Win7 EXE is not tested on an actual Windows 7 host.

**Distribution status:** `lasso1` is the previously published release. The LassoV2/LassV27 release remains pending until `lasso2` is published. The new Lasso `lasso3` workflow and release job are prepared in this branch; no Windows build or public `lasso3` release has been performed as part of this work. Release/download links must not be described as available until the corresponding tag/release exists.

### Pix2Text package

The workflow builds Pix2Text only by manual dispatch or a push whose head commit message includes `[pix2text-build]`. It uses x64 Python 3.11, CPU-only PyTorch and torchvision pins, Pix2Text requirements, PyInstaller 6.22.3, a list of collected dependency packages, and the `--check-pix2text` smoke check. The large OCR EXE is kept separate from standard 32-bit builds.

### Current public release inventory (checked 8 October 2026)

| Release/tag | Known purpose/assets | Status |
| --- | --- | --- |
| `v1.7.0-experimental` | `ScreenAnswer.exe`, `ScreenAnswer-Diagnostic.exe`; adds `free/gpt-6-luna` as an optional APInex model | Current standard prerelease |
| `v1.6.0-experimental` | `ScreenAnswer.exe`, `ScreenAnswer-Diagnostic.exe`; introduced APInex/Ollama standard test version | Previous standard prerelease |
| `v1.5.0-experimental` | `ScreenAnswer.exe`, `ScreenAnswer-Diagnostic.exe`, historical `ScreenAnswer-Groq.exe` | Older release; use v1.7 for current provider set |
| `v1.3.0-experimental` | `ScreenAnswer.exe`, `ScreenAnswer-Diagnostic.exe`, `ScreenAnswer-Pix2Text.exe` | Experimental x64 local OCR package |
| `lasso1` | `Lasso1.exe`, `LassV7.exe`, `webpull.ps1` | Public OpenRouter-only Lasso release |
| `lasso2` | Workflow is prepared for `LassoV2.exe`, `LassV27.exe`, `webpull.ps1` | Not present in public release list at check time |
| `lasso3` | Workflow is prepared for `Lasso.exe` (Win11 x64) and `LassoWin7.exe` (Win7 x86) | Not yet published; the tag runs both build jobs and attaches both EXEs |
| `v1.0.0`, `v1.0.1`, `v1.0.2`, `v1.0.3`, `v1.0.4`, `v1.1.0`, `v1.2.0`, `v1.2.1`, `v1.4.0-experimental` | Earlier standard iterations | See GitHub release notes for per-version asset/change history |

The v1.7.0 release assets do not include `screen_answer_config.json`, any API key, `servomotor`, Ollama, Ollama model files, or Pix2Text weights. The new Lasso release job likewise packages only `Lasso.exe` and `LassoWin7.exe`; it does not package user configs or credentials. Releases are experimental and do not certify inference quality, quotas, or provider billing. The current workflow defines no Authenticode-signing or separate checksum-publication step; users should verify the source and release provenance before running an EXE.

## 13. WebPull scripts

The Lasso WebPull scripts create a new folder under the user's Downloads directory, add a small README, and download only the named Lasso EXE:

- `webpull-lasso1.ps1` downloads `LassV7.exe` from the `lasso1` release.
- `webpull.ps1` is prepared to download `LassV27.exe` from `lasso2` once that release exists.
- No WebPull helper is defined for the new `lasso3` family; once published, obtain the Windows-specific EXE directly from that release's assets.

If the target folder already exists, each script creates a numbered sibling instead of overwriting it. If the download fails, the script removes the newly created folder. TLS 1.2 is requested where available. The script does not download an API key, config, or `servomotor` file. It does not perform a separate cryptographic checksum/signature verification of the EXE, so users who run a downloaded PowerShell script should inspect the script/source and release provenance first.

The intended commands are:

```powershell
irm https://github.com/Exo2v/indigo-otter-731/releases/download/lasso1/webpull.ps1 | iex
```

For `lasso2`, use the equivalent command only after verifying that the LassoV2/LassV27 release is published and its `webpull.ps1` asset is available.

## 14. User setup and troubleshooting

### Basic standard-app use

1. Download the current `ScreenAnswer.exe` from [v1.7.0-experimental](https://github.com/Exo2v/indigo-otter-731/releases/tag/v1.7.0-experimental), or run `answer_tray.py` with Python/Tkinter.
2. Open Settings from the tray and select APInex, Ollama, Mistral, or OpenRouter.
3. For APInex/Mistral/OpenRouter, enter the appropriate key (or configure the documented environment variable). Never ask anyone to paste a key into a public issue/chat.
4. For Ollama, install Ollama 0.12.7+ and run `ollama pull qwen3-vl:8b`. Start the local server and select Ollama; no key is required.
5. Read the matching upload/data-path notice, select consent, and save. Standard consent starts unchecked after each app launch.
6. Use a synthetic/non-sensitive screenshot first; press `Ctrl+Alt+S` only after checking the screen contents.

### New Lasso family (when the `lasso3` release is published)

1. Choose `Lasso.exe` for the 64-bit Windows 11 target or `LassoWin7.exe` for the 32-bit Windows 7 target. The CI workflow is configured for both; neither Windows build has been executed from this worktree yet.
2. On first launch the app creates its matching `%APPDATA%` config with blank APInex/OpenRouter keys and screenshot consent off, then opens Settings automatically because the selected provider key is missing. Choose a provider, enter its key, and explicitly enable consent if you accept the upload route. **Save** closes Settings; after a key is stored, Settings is available from the tray on demand.
3. APInex is the default provider/model. OpenRouter is limited to two explicit Gemma `:free` vision IDs; this Lasso family accepts only `free/gemini-3.8-flash` and `free/gemini-3.1-pro` on APInex. Model names are never shown in Settings: change the selected provider's `models` entry in the config and restart. The GPT-6 Luna alternative is confined to standard Screen Answer. No paid or cross-provider fallback is used; verify APInex quota/pricing in the user's account.
4. **Ctrl+Alt+S** sends the full desktop only after consent. A separate diagnostic console opens only when explicitly requested. It can contain OCR/model text or provider errors; API keys and screenshot pixels are omitted. `Ctrl+Alt+O` silently schedules cleanup of only the running executable and matching config; the tray-menu self-destruct command remains confirmation-gated.
5. The family makes chat-completions requests only; live web search and tool execution are disabled. Never package or share the per-user config, which stores keys in plaintext.

### Common failure cases

| Symptom | What to check |
| --- | --- |
| Capture blocked before a request | Enter a hosted key if needed, acknowledge the current provider/OCR notice, and save. Switching provider/OCR resets consent. |
| APInex key/account error | Check `APINEX_API_KEY` or Settings entry, account permissions, rate limit, free allowance, and billing state. A `402` should prompt account/allowance review; do not assume free status. |
| Ollama connection error | Ensure Ollama is installed and running at `127.0.0.1:11434`; the app does not install/start the service for you. |
| Ollama model not found | Pull the exact model ID (default `ollama pull qwen3-vl:8b`) and ensure the selected model supports vision. |
| Grey result after successful request | Check diagnostic output for a missing/ambiguous `ANSWER: n`, multiple questions, unreadable image, or unsupported question type. Neutral means no reliable position was extracted. |
| Pix2Text unavailable | Use Provider default, install `requirements-pix2text.txt` in the source Python environment, or run the separate bundled Pix2Text package. Model initialization may require disk space/network. |
| Capture rejected as too large | Reduce desktop resolution/number of display pixels; the program currently captures the full desktop and does not auto-crop. |
| Portable sidecar unexpectedly contains keys | It is plaintext and opt-in; remove it securely or disable portable saving. Do not include it when copying EXEs publicly. |
| Diagnostic log contains sensitive text | Clear it and review before saving/copying; OCR/final model output may echo screen content even though pixels/keys are omitted. |

## 15. Current status, risks, and next work

### Implemented in source and workflow configuration

- Standard APInex/Ollama/Mistral/OpenRouter provider set, consent UX, config filtering, and API request implementations.
- Direct Google/Gemini and Groq provider paths removed from the standard build; historical Groq release assets remain historical, not current.
- Existing Lasso1/LassV7 and LassoV2/LassV27 remain OpenRouter-only and separate. The new Lasso source adds APInex/OpenRouter, per-variant config, config-only model selection, explicit consent, and on-demand console diagnostics.
- Full-desktop capture, tray color reporting, OCR options, diagnostics, and multiple-choice parsing.
- Offline test coverage, including mocked API request formatting and new Lasso behavior. Separate Win11/x64 and Win7/x86 build/release jobs are configured.

### Not verified by this project run

- Real APInex image acceptance, account quota, billing after quota, upstream retention, real-world latency, and answer quality.
- Real Ollama inference, hardware requirements/latency, and answer quality on the target device.
- Accuracy on a representative problem set or sustained 80–120-query workload.
- Execution of the new Windows packaging/release jobs, runtime behavior on actual Windows 11 and Windows 7 machines, and whether the `lasso3` assets are published.
- Availability of a `lasso2` release/WebPull asset at the check date.

### Sensible next steps

1. Review provider terms and account settings. Test APInex with synthetic images and confirm usage/billing counters.
2. Test Ollama locally on the target Windows device, including the model load time, memory use, and answer accuracy.
3. Compare both providers using the same labeled problem set and keep records of correct, incorrect, neutral, latency, and usage.
4. Only after these tests decide whether to expand distribution or change provider/model defaults.
5. Run the `lasso3` Windows 11 and Windows 7 build jobs, then smoke-test the corresponding EXEs on their target operating systems before publishing the tag.
6. If the LassoV2/LassV27 assets are needed publicly, verify the WebPull script/release notes and publish the intended `lasso2` tag through the configured workflow.

## 16. Reference links

- [Current v1.7.0 release](https://github.com/Exo2v/indigo-otter-731/releases/tag/v1.7.0-experimental)
- [Previous v1.6.0 release](https://github.com/Exo2v/indigo-otter-731/releases/tag/v1.6.0-experimental)
- [Lasso1 release](https://github.com/Exo2v/indigo-otter-731/releases/tag/lasso1)
- [GitHub release history](https://github.com/Exo2v/indigo-otter-731/releases)
- [Detailed v1.6 APInex/Ollama implementation guide](v1.6.0-apinex-ollama-implementation-guide.md)
- [Free-model research/action plan](free-model-research-action-plan.md)
- [APInex authentication](https://apinex.bond/developers/auth), [models](https://apinex.bond/developers/models), [chat format](https://apinex.bond/developers/models/chat), [pricing](https://apinex.bond/pricing)
- [Ollama API](https://docs.ollama.com/api/chat), [vision guide](https://docs.ollama.com/capabilities/vision), [Qwen3-VL model](https://ollama.com/library/qwen3-vl)
- [OpenRouter free variants](https://openrouter.ai/docs/guides/routing/model-variants/free), [Mistral API](https://docs.mistral.ai/)
