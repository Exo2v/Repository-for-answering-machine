# Otterary version 1

Otterary is a standalone Windows tray app family, separate from Screen Answer and every Lasso release. The current no-retry release is `otterary-v1.0.1`; the original `otterary` tag remains version 1.0.0. Each release publishes two builds:

- `Otterary.exe` — Windows 11 x64, packaged with Python 3.11.
- `OtteraryWin7.exe` — Windows 7 x86, packaged with Python 3.8.10.

## Providers and setup

Otterary supports **Google Gemini** and **OpenRouter**. On first launch, its Settings window opens with API-key fields blank and screenshot-upload consent off. Select a provider, enter your own API key, review the upload notice, and save. No environment variables are required, and no credentials are bundled with either executable.

Settings are stored separately for each build at `%APPDATA%\Otterary\config.json` or `%APPDATA%\OtteraryWin7\config.json`. API keys are plain text in that per-user file; keep it private. The model ID can be edited in Settings. OpenRouter is restricted to the configured vision model IDs `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`. Gemini uses the selected Google Gemini model ID directly. Provider access, quotas, data terms, and billing can change; check the provider's current account terms. Do not assume unlimited or guaranteed-free usage.

The app sends a full-desktop image only after you trigger a capture and save consent. It uses only the selected provider; it does not switch to another provider, perform live web search, or execute tools. Only capture screens you are allowed to share, and only where AI assistance is permitted.

## Tray controls

- **Ctrl+Alt+S** captures and asks the selected provider.
- The tray icon displays options 1–4 as red, yellow, green, and blue. Grey means ready, no reliable answer, or a failed request. An answer holds for 10 seconds and then fades to grey.
- Otterary shows **no hover tooltip** and sends **no tray balloons or notifications**. The icon color is the runtime feedback.
- Double-click the tray icon or right-click and choose **Open Otterary** to show Settings.
- The diagnostic console is hidden by default. To open it, right-click the tray icon and choose **Open diagnostic console**. It opens no diagnostic page or console automatically. Logs omit API keys and screenshot pixels; review any output before sharing it.
- **Ctrl+Alt+O** silently closes Otterary and schedules deletion of only the running executable and its matching `config.json`. The per-user folder is removed only if empty. The right-click **Self-destruct Otterary…** action asks for confirmation instead.
- **Ctrl+Alt+Q** exits without deleting files.

## Request behavior

Each accepted capture makes exactly one provider HTTP attempt. Otterary does not automatically retry rate limits, temporary server errors, or other failed requests; pressing Ctrl+Alt+S again starts a separate request. Existing app families keep their own retry behavior.

## Release workflow

The `otterary` tag publishes version 1.0.0; versioned tags such as `otterary-v1.0.1` publish later Otterary releases. Windows 11 and Windows 7 jobs each run the unit tests and a packaged-app smoke check before the release job attaches the assets.
