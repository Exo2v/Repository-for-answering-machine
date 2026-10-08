# Free-Model Research, Action Plan, and Request Pipeline

**Prepared:** 8 October 2026
**Status:** APInex and local Ollama are implemented in the standard ScreenAnswer source for testing. The 65-test unit suite and syntax check pass. No APInex account, API key, or live inference request was used, and no Windows executable has been built; live provider/quota behavior remains unverified. Dedicated LassoV2/LassV27 builds remain OpenRouter-only.

## Executive summary

The target workload is approximately **80–120 screenshot questions in four hours** (one every two or three minutes). APInex publicly advertises **1 million daily tokens for its free-category models**. On a simple division, that is a budget of **12,500 tokens per question at 80 questions** or **about 8,333 per question at 120**. Its published free-tier request rate is 5 requests/minute, well above the planned 0.33–0.5 requests/minute.

**Conclusion:** 1 million tokens *could* cover the session, but it is not yet verified for this application. Each request includes a full desktop image, the instruction prompt, model reasoning, and the answer. Image-token accounting and the free allowance's model weights must be measured with the actual request shape. APInex's public pages also show a pricing/allowance ambiguity that should be clarified before relying on it.

The open-source **FreeLLMAPI** project is a second, more resilient architecture candidate: it runs a local gateway and can distribute requests among a user's own provider keys, with vision-aware routing and automatic failover. Its stated aggregate model capacity is not a guarantee for this workload, though; provider caps, terms, and model quality still apply, and its documentation warns that free-tier performance can degrade as quotas are used.

**Implementation status:** the standard ScreenAnswer app now offers APInex (default), local Ollama, Mistral, and OpenRouter. APInex is restricted to two curated free vision aliases; Ollama uses a local vision model without a key. Direct Google/Gemini and Groq providers were removed from the standard app. The APInex base64 request and Ollama local request are covered by offline unit tests only. **Next:** validate APInex with a user's own account/key and synthetic screenshots, verify measured usage/quotas and data terms, run Ollama against an installed local model, then build/test the Windows executables. Do not treat these provider integrations as live-verified. FreeLLMAPI remains research-only; it is not integrated and is not an automatic fallback.

## 1. Goal and existing constraints

- About **80–120 requests per four-hour session**.
- Requests are screenshots of problems; the solver should identify relevant facts, select the concept, calculate, check, and return a concise answer.
- Model selection must remain in configuration, not be displayed or editable in the Lasso Settings GUI.
- First-run keys must be blank; never package credentials or a configured user file.
- Screenshot consent remains off until the user explicitly enables it.
- No live web search or tool execution in the solving request.
- Keep the Lasso tray behavior: answer color is the normal tray feedback; Diagnostics stays on-demand.
- The **standard ScreenAnswer** provider choices are APInex, local Ollama, Mistral, and OpenRouter. Direct Google/Gemini and Groq support has been removed from this standard test version. The direct model alias `free/gemini-3.8-flash` is still an APInex catalog ID; it does not use Google's API or require a Google key. OpenRouter's allowlisted `google/gemma-4-...:free` model IDs remain behind OpenRouter.
- Dedicated `LassoV2.exe` / `LassV27.exe` builds remain OpenRouter-only, with model selection in their config files and no model control in Settings. Legacy Lasso1/LassV7 behavior and config paths are unchanged. FreeLLMAPI remains research-only and is not a configured fallback.
- The current app captures the full virtual desktop in memory. Do not assume a crop or a reduced capture is in scope; measure the current capture first.

## 2. What I learned from the resources

### A. APInex: hosted API with a claimed daily free allowance

Sources: [APInex home](https://apinex.bond/), [pricing](https://apinex.bond/pricing), [API/model docs](https://apinex.bond/developers/models), [chat request docs](https://apinex.bond/developers/models/chat), [billing](https://apinex.bond/developers/models/billing), [rate limits](https://apinex.bond/developers/errors), [privacy policy](https://apinex.bond/legal/privacy), and [terms](https://apinex.bond/legal/terms).

- The public site says every account receives **1M tokens/day for free-category models**. Its free-model list includes `free/gemini-3.8-flash`.
- The login page currently requires a personal `@gmail.com` Google account to sign in and create an API key.
- It advertises an OpenAI-compatible API at `https://api.apinex.bond/v1`. Its chat documentation describes image content parts and lists Gemini 3.8 as supporting images and configurable reasoning. The docs also describe a `reasoning_effort` request parameter.
- The published free-tier limit is **5 requests/minute per IP**. The planned request cadence is far below this limit.
- APInex's billing documentation says free models draw from a daily allowance using a weighted input-plus-output calculation, and reasoning tokens count in generated output. Responses expose token-usage information. The exact per-model allowance weight and image-token behavior still need to be checked against an actual response and account counter.
- **Public-page ambiguity:** the pricing page marks free-category input/output as free within the daily allowance, while the live model-price page labels some of the same `free/...` IDs with nonzero *retail* prices. This may be reference pricing rather than what a free-tier account pays, but the pages do not clearly explain the difference or what happens after the daily allowance is exhausted. The billing guide says free models draw from the daily allowance rather than the wallet. Confirm the account's actual counter and exhaustion behavior, and configure a spend limit before a sustained test.
- The `/keys` page redirects to sign-in; the published auth instructions say API keys are created after login and shown only once. Do not send an API key in chat or commit it to this repository.
- APInex's privacy policy says request metadata is collected, prompts/completions may be processed to fulfill requests, and model/tool upstreams may receive data. It says personal information is not sold, but the public pages reviewed do not establish a prompt-retention period or a no-training guarantee. Screenshots would pass through APInex and an upstream model provider; review the terms and privacy notice before consenting.
- Its terms say service availability and models can change, provide no availability guarantee, and describe prepaid balances as generally non-refundable. Treat the advertised daily allowance as a claim to test, not an SLA.

**Image-format check:** APInex's chat example documents `image_url`, while the public example uses a remote image URL. The standard ScreenAnswer implementation now sends a base64 data URL for an in-memory screenshot. Unit tests verify the payload shape but do not prove APInex accepts it; confirm with a synthetic image and a real account before using personal screenshots. Do not upload screenshots to a separate image host just to make the API work.

### B. FreeLLMAPI: self-hosted multi-provider gateway

Sources: [repository and README](https://github.com/tashfeenahmed/freellmapi), [API reference](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/api/01-rest-api.md), [architecture/limitations/terms review](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/architecture/00-high-level-index.md), and [install guide](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/install/01-install.md).

- The project describes itself as a **local, single-user OpenAI-compatible gateway**. A typical local endpoint is `http://localhost:3001/v1`; it uses provider API keys supplied by the operator rather than giving the Lasso app one shared third-party account.
- The README currently claims 34 free providers, 635 free model endpoints, and about 7.4B monthly tokens across the catalog. These are the project's aggregated catalog figures, **not a promise that 7.4B vision/reasoning tokens are available to one user**.
- It tracks provider quotas and health, filters image requests to vision-capable models, and can fail over to the next model in a configured chain. Its API documentation describes base64 `data:` image URLs as well as remote image URLs. Responses identify the model/provider that actually served the request.
- The project claims provider keys are encrypted at rest with AES-256-GCM in local SQLite; the operator must protect the encryption key and database backups. The local gateway should remain loopback-only and single-user, not be exposed to the public internet or shared with other people.
- The README explicitly warns of variable latency, no SLA, changing provider free tiers, and **quality degradation as stronger models exhaust their daily caps**. Free installations use a monthly catalog snapshot, so updates can lag the live catalog. Its terms review is informational and not legal advice; the user remains subject to each upstream provider's terms.
- Installation requires Node.js 20+ or Docker, unless using the project's desktop package. **Windows 7 compatibility is not established by the pages reviewed**; do not assume the local gateway can run on the `LassV27.exe` machine without a separate compatibility test.

This option is promising for failover across genuinely independent provider quotas, but the fallback chain must contain only verified **free, vision-capable, reasoning-capable** models. A generic `auto` chain is not sufficient for this app unless the vision and pricing filters are confirmed.

### C. Other supplied resources

- **[awesome-freellm-apis](https://github.com/open-free-llm-api/awesome-freellm-apis)** is a discovery catalog, not an inference gateway or a guarantee of a provider's current free access. Its README describes daily updates and modality/rate-limit fields, but its displayed model/provider totals are inconsistent in different sections. Use it to find candidates, then verify each candidate with the provider's own docs.
- **[Bytez image-to-text catalog](https://bytez.com/models?task=image-to-text)** is not the same task as answering a question about a screenshot. Bytez's [multimodal image-text-to-text guide](https://docs.bytez.com/model-api/docs/task/image-text-to-text) is the more relevant input format because it accepts both image and text. Bytez's [billing docs](https://docs.bytez.com/model-api/docs/billing) describe a $1 free credit allowance refreshed every four weeks, with open models billed per inference second and free-plan open-model access limited by model size. That is less predictable for a repeated 80–120 screenshot session than a verified daily token allowance.
- **Ollama local inference** uses its native `http://127.0.0.1:11434/api/chat` endpoint and accepts base64 images in `messages[].images`; the app does not send screenshots to a cloud model API when this backend is selected. The test version defaults to `qwen3-vl:8b`, which requires Ollama 0.12.7 or later and a separate multi-gigabyte model download. The request body is covered by offline tests, but local inference has not been run in this workspace. See the [Ollama chat API](https://docs.ollama.com/api/chat), [vision guide](https://docs.ollama.com/capabilities/vision), and [Qwen3-VL model card](https://ollama.com/library/qwen3-vl).
- The standard app and dedicated Lasso builds retain the current OpenRouter free variants `google/gemma-4-31b-it:free` and `google/gemma-4-26b-a4b-it:free`; these are still routed through OpenRouter. OpenRouter documents a 50 free-model requests/day account cap below $10 in lifetime credit purchases, rising to 1,000/day at the higher tier; that platform cap is relevant to the 80–120 request target. See [OpenRouter rate limits](https://openrouter.ai/docs/api_reference/limits).

## 3. Is 1M APInex tokens enough?

APInex's billing guide defines free allowance use from input plus output tokens, multiplied by a model-specific weight. For planning, use the full allowance divided by the requested number of screenshots:

| Questions in 4 hours | Average allowance per question from 1M/day |
| ---: | ---: |
| 80 | 12,500 weighted tokens |
| 100 | 10,000 weighted tokens |
| 120 | about 8,333 weighted tokens |

This budget must cover the **whole request**: system prompt, user prompt, screenshot/image tokens, any reasoning counted as output, and final explanation. Retries may also consume allowance; that behavior should be measured rather than assumed. For a 120-question session, a prudent pilot target is an average of **about 6,500 weighted tokens or less per request**, leaving roughly 20% of the nominal daily allowance for retries and variance.

**Practical answer:** 1M/day looks plausible for short prompts and ordinary screen captures, but it cannot be confirmed from the public headline alone. A full multi-monitor/high-resolution desktop image plus high reasoning could push the average over the 8,333-token break-even point. The definitive measurement is the API's returned usage and remaining free allowance after representative requests.

The 5 RPM free-tier rate limit is not the bottleneck: one request every 2–3 minutes is only 0.33–0.5 RPM. The unresolved risks are image-token accounting, per-model allowance weight, provider capacity, the behavior at daily quota exhaustion, and privacy/retention.

## 4. Candidate architecture comparison

| Option | What it offers | Fit for 80–120 questions | Main caution |
| --- | --- | --- | --- |
| **APInex hosted free category** | Simple OpenAI-compatible endpoint; public claim of 1M free-category tokens/day; Gemini 3.8 image/reasoning support is documented | Plausible if measured average usage is below the per-question budget; 5 RPM is ample | Third-party screenshot relay; unclear prompt retention; inconsistent pricing/allowance surfaces; base64 and quota-exhaustion behavior need live testing |
| **Ollama local** | Local chat endpoint with base64 vision input; no API key or hosted quota | Could avoid per-request cloud quotas if the computer can run the model efficiently | Requires Ollama and several gigabytes of model files; hardware/latency/quality are untested here |
| **FreeLLMAPI local gateway** | Routes among the user's own free provider keys; vision filtering, quota-aware fallback, and model/provider reporting | Potentially more resilient if enough independent vision-capable quotas are enabled | Not integrated; free-tier quotas and terms remain provider-specific; self-hosting, local key security, and Windows compatibility need setup/testing |
| **OpenRouter current path** | Already integrated, one API key, exact free model IDs | Under its lower daily cap it does not cover 80–120 calls; the higher tier does | Requests are capped; switching model IDs alone does not remove account-level quota |
| **Bytez** | Broad model catalog, unified model API | Useful for small experiments, not yet shown to cover this workload at no cost | Credit-based free plan and per-second open-model billing; image-to-text catalog is not necessarily VQA |

## 5. Current test plan and remaining gates

### Phase 0 — Source implementation status

- [x] Standard ScreenAnswer offers APInex (default), local Ollama, Mistral, and OpenRouter.
- [x] Direct Google/Gemini API and Groq provider implementations/options were removed from the standard app. APInex's `free/gemini-...` IDs are APInex aliases; Google-family model IDs behind APInex/OpenRouter are not direct Google API integrations.
- [x] APInex and OpenRouter use exact vision-model allowlists; there is no paid-model or cross-provider fallback. Ollama uses a loopback API and requires no API key.
- [x] Legacy provider credentials/models are filtered from portable config; retired Google/Groq keys are not reused as APInex keys. User keys and config files are not packaged.
- [x] APInex and Ollama request construction, config migration, provider registry, and safety behavior have offline unit coverage. `python -m unittest discover -s tests -v` passes (67 tests); `python -m py_compile answer_tray.py` passes.
- [x] Dedicated LassoV2/LassV27 builds remain OpenRouter-only. Their Settings GUI stays model-free; models remain in their per-user config files. Lasso startup, consent, tray feedback, cleanup scope, and config paths are not expanded by this integration.
- [ ] Build and smoke-test the Windows executables in CI or on a Windows machine. No Windows build has run yet.

### Phase 1 — APInex live compatibility and quota pilot

- [ ] The user creates an APInex account/key locally; keep the secret out of chat, Git, release assets, and shared screenshots.
- [ ] With a synthetic/non-sensitive screenshot, verify APInex accepts the app's base64 data URL and returns the expected final chat text. Unit tests verify only the payload shape; they do not prove live compatibility.
- [ ] Confirm the selected exact free vision model, image input, reasoning behavior, `usage` fields, free-allowance counter, and account pricing with a real account.
- [ ] Resolve the public free-allowance/retail-price discrepancy and verify what happens at quota exhaustion. Do not assume free calls can never debit a wallet.
- [ ] Run 10–20 known-answer questions at a safe cadence. Record model ID, answer accuracy, latency, input/output/reasoning usage, allowance remaining, and any 402/429/upstream errors.

### Phase 2 — Local Ollama pilot

- [ ] Install a current Ollama build (the selected `qwen3-vl:8b` model requires Ollama 0.12.7+) and pull the model separately; no Ollama runtime or weights are bundled.
- [ ] Confirm Ollama listens on `127.0.0.1:11434`, then send a synthetic screenshot and verify the expected `messages[].images` base64 payload and final response.
- [ ] Measure model load time, first-token/total latency, memory requirements, and answer accuracy on the target computer. The model download is several gigabytes; requirements vary by platform and quantization.
- [ ] Verify the app works without an API key and fails clearly if the service/model is missing. The app's request is to loopback; do not configure an untrusted remote endpoint.

### Phase 3 — Prompt and model-quality evaluation

- [ ] Compare APInex and Ollama against the same non-sensitive set: arithmetic, algebra, physics/science concepts, irrelevant details, signs/units, and image/diagram reading.
- [ ] Require a concise, verifiable solution—not an unbounded chain-of-thought transcript. Suggested response sections: `TRANSCRIPTION`, `RELEVANT FACTS`, `IRRELEVANT DETAILS`, `CONCEPT`, `CALCULATION`, `CHECK`, `ANSWER`.
- [ ] Review whether the multiple-choice parser matches the intended questions. It expects one of four choices and an `ANSWER: 1–4` line; free-response support is out of scope.
- [ ] Keep the standard app's provider/model selector behavior; for dedicated Lasso builds, keep model selection only in the matching config file, never in Settings.

### Phase 4 — Four-hour/release gate

Before broad use, verify:

- The APInex route accepts the actual in-memory screenshot format; the Ollama route works with the chosen local model.
- APInex average usage is **≤6,500 weighted tokens/request** for the 120-question target, or measured account data provides at least 20% quota headroom.
- No paid fallback or cross-provider fallback can occur. Exhausted/failed requests finish safely with a neutral result.
- APInex's quota, privacy terms, and wallet behavior are acceptable to the user; screenshot consent remains off until explicitly saved.
- Windows builds pass smoke checks; first-run keys remain blank and no sidecar/config/secret is included in release assets.

FreeLLMAPI remains a researched alternative only; it is not integrated and must not be treated as an automatic fallback. Begin with 10–20 representative questions before any full 80–120-query session.

## 6. Implemented request pipeline (standard ScreenAnswer)

```text
User explicitly acknowledges upload notice + triggers Ctrl+Alt+S
                         │
                         ▼
Capture full virtual desktop → encode PNG in memory (no screenshot file)
                         │
                         ▼
Optional Pix2Text OCR runs locally; transcript is bounded and used as context
                         │
                         ▼
User-selected standard provider
  ┌──────────────────────┼────────────────────┬──────────────────────┐
  ▼                      ▼                    ▼                      ▼
APInex HTTPS          Ollama loopback       Mistral HTTPS         OpenRouter HTTPS
curated free vision   local vision model    OCR + chat by default curated :free IDs
  └──────────────────────┴────────────────────┴──────────────────────┘
                         │
                         ▼
No live web search/tools; provider-specific bounded error handling;
no paid-model or cross-provider fallback
                         │
                         ▼
Parse explicit `ANSWER: n`; ambiguous/failed response → neutral result
                         │
                         ▼
Tray color result; optional diagnostics may show final text/provider errors,
but omit API keys and screenshot pixels
```

Standard ScreenAnswer can select a provider/model in its Settings GUI. The dedicated Lasso builds remain separate: OpenRouter-only, no model field in Settings, and model selection in each matching per-user config. APInex uses `free/gemini-3.8-flash` by default and `free/gemini-3.1-pro` as its second allowed ID; these are APInex catalog IDs. Ollama defaults to `qwen3-vl:8b` and uses no key. OpenRouter remains restricted to the existing explicit Gemma `:free` IDs. Mistral's provider-default OCR makes a separate hosted OCR call; optional Pix2Text OCR runs locally and skips that Mistral OCR call. No backend is invoked until the user triggers capture after acknowledging the selected data path.

## 7. Remaining decisions before relying on the test build

- [ ] **Interpretation of “remove Google”:** the direct Google Gemini provider/key is removed. The APInex default model ID includes `gemini`, and OpenRouter's allowlist includes Google Gemma IDs, but neither route uses Google's direct API. If all Google-family model IDs are prohibited—not just the direct provider—the APInex/OpenRouter model allowlists and defaults need a different explicitly approved vision model.
- [ ] **APInex:** Is sending the full desktop screenshot through APInex and its upstream provider acceptable after reviewing its current terms/privacy policy? Does a real account confirm free quota and no unexpected wallet debit?
- [ ] **Ollama:** Does the user's test computer have enough disk, memory, and compute for the selected local vision model and acceptable latency?
- [ ] **Quota and quality:** Is a measured best-effort free quota acceptable, and what minimum answer accuracy/maximum latency should the pilot require?
- [ ] **Future gateway:** Keep FreeLLMAPI out of this test version unless a later request explicitly approves it as a separate option.

## Sources reviewed

All reviewed on **8 October 2026**. Public documentation only; no APInex account, key, or live inference request was used.

- [FreeLLMAPI GitHub repository / README](https://github.com/tashfeenahmed/freellmapi)
- [FreeLLMAPI REST API — vision/image input and routing](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/api/01-rest-api.md#vision--image-input)
- [FreeLLMAPI architecture, limitations, and provider ToS review](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/architecture/00-high-level-index.md)
- [FreeLLMAPI installation and data/key handling](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/install/01-install.md)
- [APInex home](https://apinex.bond/), [pricing](https://apinex.bond/pricing), [models](https://apinex.bond/developers/models), [chat API](https://apinex.bond/developers/models/chat), [billing](https://apinex.bond/developers/models/billing), [errors and rate limits](https://apinex.bond/developers/errors), [auth](https://apinex.bond/developers/auth), [privacy](https://apinex.bond/legal/privacy), and [terms](https://apinex.bond/legal/terms)
- [awesome-freellm-apis catalog](https://github.com/open-free-llm-api/awesome-freellm-apis)
- [Bytez image-to-text catalog](https://bytez.com/models?task=image-to-text), [multimodal vision API](https://docs.bytez.com/model-api/docs/task/image-text-to-text), and [billing](https://docs.bytez.com/model-api/docs/billing)
- [OpenRouter free-model rate limits](https://openrouter.ai/docs/api_reference/limits)
- [Ollama chat API](https://docs.ollama.com/api/chat), [vision capabilities](https://docs.ollama.com/capabilities/vision), and [Qwen3-VL model card](https://ollama.com/library/qwen3-vl)
