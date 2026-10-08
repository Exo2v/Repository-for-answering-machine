# Screen Answer — Whole-Project Guide

**Prepared:** 8 October 2026<br>
**Project:** Screen Answer (repository historically named `Repository-for-answering-machine`; GitHub resolves to `Exo2v/indigo-otter-731`)<br>
**Current standard release:** [v1.6.0-experimental](https://github.com/Exo2v/indigo-otter-731/releases/tag/v1.6.0-experimental)<br>
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

- **Standard Screen Answer:** a general Windows app where the user can choose among hosted providers and a local model. In v1.6.0, APInex is the default and Ollama is available for local inference. Mistral and OpenRouter remain available.
- **Lasso variants:** separate tray-only builds with a narrower, OpenRouter-only configuration model. They preserve dedicated per-user settings, a model value in the config file (not the Settings GUI), explicit upload consent, and variant-specific cleanup/notification behavior.
- **Optional Pix2Text build:** a much larger experimental 64-bit build that adds local OCR. OCR extracts text and formulas; it does not solve the problem. The solver still receives the screenshot and, depending on provider, its OCR transcript.
- **Diagnostic build:** the standard program with a live diagnostics window opened automatically, for detailed testing of captures, OCR, network requests, response parsing, and errors.

The direct Google Gemini and Groq integrations were removed from the standard v1.6.0 test version because they were not working for the user. This is a provider change, not a rule banning every Google-family model name: APInex's default catalog alias still contains `gemini`, and OpenRouter's approved models still contain `google/gemma`. Those requests go through APInex or OpenRouter, not Google's direct API. If all Google-family model IDs are prohibited, the model choices must be replaced explicitly.

## 3. Product/build families at a glance

| Family | Main executables | Providers | Settings and behavior | Distribution status |
| --- | --- | --- | --- | --- |
| Standard | `ScreenAnswer.exe` | APInex (default), Ollama (local), Mistral, OpenRouter | Provider/model/OCR controls in standard Settings; consent starts off for every run | Current `v1.6.0-experimental` release |
| Standard diagnostics | `ScreenAnswer-Diagnostic.exe` | Same standard provider set | Same app, but opens the live diagnostic window at startup | Included in `v1.6.0-experimental` |
| Optional local OCR | `ScreenAnswer-Pix2Text.exe` | Same solver set; Pix2Text OCR is selected by default in that named build | 64-bit Windows 10+ experimental package; large dependencies, model weights downloaded separately | Published in `v1.3.0-experimental`; source/workflow can build it again on demand |
| Legacy Lasso | `Lasso1.exe`, `LassV7.exe` | OpenRouter only | Per-user config; Settings opens only on demand; no model field in GUI; `LassV7` suppresses balloons/tooltips | Public `lasso1` release |
| Newer Lasso design | `LassoV2.exe`, `LassV27.exe` | OpenRouter only | Per-user config; Settings opens only on demand; no model field in GUI; `LassV27` suppresses balloons/tooltips | Workflow and WebPull script exist; no `lasso2` release/tag was listed on GitHub as of 8 October 2026. Verify availability before using the `lasso2` download URL. |

The names `LassV7` and `LassV27` identify 32-bit Python 3.8.10 Windows 7-compatible targets. The modern Windows variants are also built as 32-bit executables by the current workflows. The Pix2Text build is a separate 64-bit Windows 10+ package because of its heavier dependency stack.

### Project history and rationale

- **v1.0.0–v1.2.1:** early iterations of the standard Windows tray helper. Consult the individual release notes for precise changes; this guide does not infer undocumented feature-by-feature history.
- **v1.3.0-experimental:** added a separate Pix2Text executable, exploring local text/formula extraction without replacing the model-based solver.
- **v1.4.0-experimental and v1.5.0-experimental:** continued the standard experimental line. The v1.5.0 release included standard/diagnostic builds and a historical Groq executable.
- **v1.6.0-experimental:** replaced direct Google Gemini and Groq integrations in the standard test version with APInex and local Ollama, while keeping Mistral and OpenRouter as choices. This tests a hosted intermediary and an on-device alternative without changing the separate Lasso provider scope.
- **Lasso releases/builds:** evolved as distinct OpenRouter-only tray products rather than settings presets inside the standard app. Lasso1/LassV7 are publicly released; the LassoV2/LassV27 build flow exists but its release is not currently published.

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

APInex is the standard default. The app restricts it to two configured IDs:

- `free/gemini-3.8-flash` (default)
- `free/gemini-3.1-pro`

It sends an OpenAI-compatible chat-completions request with the PNG as an `image_url` base64 data URL, `temperature: 0`, `reasoning_effort: "medium"`, and a 2,048-token output cap. The request contains no tool/plugin declaration. The key is sent in an HTTP Bearer Authorization header and never embedded in the EXE.

The app handles authentication, account quota, payload-size, rate-limit, missing-model, and temporary-upstream errors with provider-specific messages. Transient hosted calls are bounded to three attempts where the response class is retryable. The release tests mocked the HTTP endpoint; they did not make an APInex inference call.

APInex publicly advertises a free-category daily allowance and a 5-request/minute/IP rate limit. Its public pricing/model materials have shown a discrepancy between free-category allowance claims and nonzero retail prices beside some `free/...` IDs. Account billing and post-quota behavior remain unverified. A model name containing `free` is not a guarantee of zero cost; check the account usage/balance before sustained use.

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

Each Lasso executable has its own per-user `config.json`:

| Executable | Config path |
| --- | --- |
| `Lasso1.exe` | `%APPDATA%\Lasso1\config.json` |
| `LassV7.exe` | `%APPDATA%\LassV7\config.json` |
| `LassoV2.exe` | `%APPDATA%\LassoV2\config.json` |
| `LassV27.exe` | `%APPDATA%\LassV27\config.json` |

A first-run config has a blank OpenRouter key, the default allowlisted Gemma `:free` model, and `allow_screenshot_uploads: false`. The only accepted Lasso model IDs are `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`. Lasso config writes are atomic; a key saved there is plaintext, so protect the per-user config as a credential file. Lasso builds ignore environment keys. The model can only be changed by editing the matching config file and restarting; it is not shown in the Settings GUI. A missing/unapproved model migrates to the safe default and clears old screenshot consent when the route/model changes.

Example first-run Lasso config:

```json
{
  "provider": "openrouter",
  "api_keys": {"openrouter": ""},
  "models": {"openrouter": "google/gemma-4-31b-it:free"},
  "allow_screenshot_uploads": false
}
```

## 8. Consent, privacy, and logging

Consent describes the actual recipient. Changing the selected provider or OCR backend clears consent in the standard UI; saving the new selection is required before a later capture. The standard app never persists consent. Lasso consent is stored in its per-user config and begins false. Full-screen upload notices should be read carefully; do not capture screens the user is not permitted to share.

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

For Lasso, right-click **Open** reveals Settings on demand. The menu also opens the matching config file/folder and can show Diagnostics on demand. Saving Settings hides/closes the window. The tray-menu self-destruct action asks for confirmation, while `Ctrl+Alt+O` does not prompt or show an app notification. Cleanup targets only the running Lasso EXE and its matching config file; a directory is removed only if empty, and unexpected files are left alone. If cleanup cannot be scheduled, the app stays open.

LassV7 and LassV27 suppress app-generated notification-area balloons and hover tooltips; their icon color is the runtime feedback. Standard builds and the other Lasso variants (`Lasso1` and `LassoV2`) may show normal status notifications and tooltips.

## 10. Repository map

| Path | Role |
| --- | --- |
| `answer_tray.py` | Main application, provider adapters, Windows tray/hotkeys, Tkinter Settings/diagnostics, capture/OCR, config migration, parsing, build smoke checks |
| `tests/test_answer_tray.py` | `unittest` coverage for providers, config, consent, Lasso behavior, parsing, image encoding, OCR, cleanup, and diagnostic modes |
| `README.md` | Quick user guide, downloads, provider descriptions, Lasso and Pix2Text overview, source/build instructions |
| `docs/project-guide.md` | This project-wide user/maintainer guide |
| `docs/v1.6.0-apinex-ollama-implementation-guide.md` | Focused technical detail for v1.6 APInex/Ollama, request shapes, testing status, and pilot plan |
| `docs/free-model-research-action-plan.md` | APInex allowance/pricing research, local-gateway comparison, quota plan, and open validation questions |
| `.github/workflows/windows-release.yml` | Standard, Lasso, Pix2Text Windows build and release workflows |
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

The suite has 67 tests as of v1.6.0. Provider tests mock `urllib.request.urlopen`; they inspect payloads, model allowlists, redaction, retries, local endpoint errors, OCR context, and answer parsing without using a real key or service. The suite also covers config migration, no-key Ollama Settings behavior, upload consent, Lasso config paths and UI behavior, tray notification suppression, self-cleanup scope, PNG encoding, and Pix2Text API import/behavior using mocks.

The EXEs support build smoke-check flags:

- `--check-apinex-ollama` — checks standard defaults, provider registry, endpoints, valid default models, and keyless Ollama policy.
- `--check-openrouter-support` — checks OpenRouter provider/key/model/endpoint wiring.
- `--check-lasso1-build`, `--check-lassv7-build`, `--check-lassov2-build`, `--check-lassv27-build` — verify expected executable identity, provider scope, model policy, config folder, diagnostics mode, and where relevant Python version/bitness.
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

The same workflow defines Lasso1/LassV7 and LassoV2/LassV27 build jobs. Each pair uses x86 Python 3.8.10 and PyInstaller 5.13.2, runs the test suite and build smoke checks, validates its PowerShell script, and uploads two EXEs plus a renamed `webpull.ps1` artifact. Tags `lasso1` and `lasso2` publish their respective Lasso releases. The workflow also permits manual dispatch or matching commit-message markers (`[lasso1-build]`, `[lasso2-build]`) to build the pairs.

**Current distribution caveat:** the public GitHub release list as checked on 8 October 2026 includes the `lasso1` release but does not show a `lasso2` tag/release. The source and workflow for LassoV2/LassV27 exist, but their release/WebPull URL should be considered pending until the `lasso2` release is actually published. The README now distinguishes this prepared build flow from a published download.

### Pix2Text package

The workflow builds Pix2Text only by manual dispatch or a push whose head commit message includes `[pix2text-build]`. It uses x64 Python 3.11, CPU-only PyTorch and torchvision pins, Pix2Text requirements, PyInstaller 6.22.3, a list of collected dependency packages, and the `--check-pix2text` smoke check. The large OCR EXE is kept separate from standard 32-bit builds.

### Current public release inventory (checked 8 October 2026)

| Release/tag | Known purpose/assets | Status |
| --- | --- | --- |
| `v1.6.0-experimental` | `ScreenAnswer.exe`, `ScreenAnswer-Diagnostic.exe`; APInex/Ollama standard test version | Current standard prerelease |
| `v1.5.0-experimental` | `ScreenAnswer.exe`, `ScreenAnswer-Diagnostic.exe`, historical `ScreenAnswer-Groq.exe` | Older release; use v1.6 for current provider set |
| `v1.3.0-experimental` | `ScreenAnswer.exe`, `ScreenAnswer-Diagnostic.exe`, `ScreenAnswer-Pix2Text.exe` | Experimental x64 local OCR package |
| `lasso1` | `Lasso1.exe`, `LassV7.exe`, `webpull.ps1` | Public OpenRouter-only Lasso release |
| `lasso2` | Workflow is prepared for `LassoV2.exe`, `LassV27.exe`, `webpull.ps1` | Not present in public release list at check time |
| `v1.0.0`, `v1.0.1`, `v1.0.2`, `v1.0.3`, `v1.0.4`, `v1.1.0`, `v1.2.0`, `v1.2.1`, `v1.4.0-experimental` | Earlier standard iterations | See GitHub release notes for per-version asset/change history |

The v1.6.0 release assets do not include `screen_answer_config.json`, any API key, `servomotor`, Ollama, Ollama model files, or Pix2Text weights. The release is experimental and does not certify inference quality, quotas, or provider billing. The current workflow defines no Authenticode-signing or separate checksum-publication step; users should verify the source and release provenance before running an EXE.

## 13. WebPull scripts

The Lasso WebPull scripts create a new folder under the user's Downloads directory, add a small README, and download only the named Lasso EXE:

- `webpull-lasso1.ps1` downloads `LassV7.exe` from the `lasso1` release.
- `webpull.ps1` is prepared to download `LassV27.exe` from `lasso2` once that release exists.

If the target folder already exists, each script creates a numbered sibling instead of overwriting it. If the download fails, the script removes the newly created folder. TLS 1.2 is requested where available. The script does not download an API key, config, or `servomotor` file. It does not perform a separate cryptographic checksum/signature verification of the EXE, so users who run a downloaded PowerShell script should inspect the script/source and release provenance first.

The intended commands are:

```powershell
irm https://github.com/Exo2v/indigo-otter-731/releases/download/lasso1/webpull.ps1 | iex
```

For `lasso2`, use the equivalent command only after verifying that the LassoV2/LassV27 release is published and its `webpull.ps1` asset is available.

## 14. User setup and troubleshooting

### Basic standard-app use

1. Download the current `ScreenAnswer.exe` from [v1.6.0-experimental](https://github.com/Exo2v/indigo-otter-731/releases/tag/v1.6.0-experimental), or run `answer_tray.py` with Python/Tkinter.
2. Open Settings from the tray and select APInex, Ollama, Mistral, or OpenRouter.
3. For APInex/Mistral/OpenRouter, enter the appropriate key (or configure the documented environment variable). Never ask anyone to paste a key into a public issue/chat.
4. For Ollama, install Ollama 0.12.7+ and run `ollama pull qwen3-vl:8b`. Start the local server and select Ollama; no key is required.
5. Read the matching upload/data-path notice, select consent, and save. Standard consent starts unchecked after each app launch.
6. Use a synthetic/non-sensitive screenshot first; press `Ctrl+Alt+S` only after checking the screen contents.

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

### Implemented and verified in the code/release workflow

- Standard APInex/Ollama/Mistral/OpenRouter provider set, consent UX, config filtering, and API request implementations.
- Direct Google/Gemini and Groq provider paths removed from the standard build; historical Groq release assets remain historical, not current.
- Dedicated Lasso provider scope remains OpenRouter-only and separate from standard settings.
- Full-desktop capture, tray color reporting, OCR options, diagnostics, and multiple-choice parsing.
- Offline tests and Windows packaging/smoke checks.

### Not verified by this project run

- Real APInex image acceptance, account quota, billing after quota, upstream retention, real-world latency, and answer quality.
- Real Ollama inference, hardware requirements/latency, and answer quality on the target device.
- Accuracy on a representative problem set or sustained 80–120-query workload.
- Availability of a `lasso2` release/WebPull asset at the check date.

### Sensible next steps

1. Review provider terms and account settings. Test APInex with synthetic images and confirm usage/billing counters.
2. Test Ollama locally on the target Windows device, including the model load time, memory use, and answer accuracy.
3. Compare both providers using the same labeled problem set and keep records of correct, incorrect, neutral, latency, and usage.
4. Only after these tests decide whether to expand distribution or change provider/model defaults.
5. If the LassoV2/LassV27 assets are needed publicly, verify the WebPull script/release notes and publish the intended `lasso2` tag through the configured workflow.

## 16. Reference links

- [Current v1.6.0 release](https://github.com/Exo2v/indigo-otter-731/releases/tag/v1.6.0-experimental)
- [Lasso1 release](https://github.com/Exo2v/indigo-otter-731/releases/tag/lasso1)
- [GitHub release history](https://github.com/Exo2v/indigo-otter-731/releases)
- [Detailed v1.6 APInex/Ollama implementation guide](v1.6.0-apinex-ollama-implementation-guide.md)
- [Free-model research/action plan](free-model-research-action-plan.md)
- [APInex authentication](https://apinex.bond/developers/auth), [models](https://apinex.bond/developers/models), [chat format](https://apinex.bond/developers/models/chat), [pricing](https://apinex.bond/pricing)
- [Ollama API](https://docs.ollama.com/api/chat), [vision guide](https://docs.ollama.com/capabilities/vision), [Qwen3-VL model](https://ollama.com/library/qwen3-vl)
- [OpenRouter free variants](https://openrouter.ai/docs/guides/routing/model-variants/free), [Mistral API](https://docs.mistral.ai/)
