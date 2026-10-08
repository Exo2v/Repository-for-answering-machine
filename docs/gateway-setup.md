# Gateway Setup — FreeLLMAPI + Screen Answer v1

**Prepared:** 8 October 2026
**Scope:** get the FreeLLMAPI gateway running on the target Windows machine, wire Screen Answer v1 (`screenanswer` package) to it, and make **live web search** work end-to-end. Companion to [freellmapi-gateway-architecture.md](freellmapi-gateway-architecture.md).

---

## 1. API budget per question (read this first)

Screen Answer v1 makes **exactly one API call per question**: one `POST /v1/chat/completions` to the gateway, which forwards one request to one upstream model. The `google_search` grounding tool rides *inside* that same request — web search adds **zero** extra calls. There is no OCR call.

Retries (max 3 attempts) happen only on `429`/`5xx`, but **failed attempts still consume the provider's rate limit**. With failover, one question can cost up to 3 attempts spread across providers.

**Budgeting for OpenRouter's 50 requests/day (sub-$10 tier):** that is at most 50 answered questions per day via OpenRouter, and less if any attempt is retried. The 80–120 questions / 4 h target therefore **cannot** run on OpenRouter alone. Do this instead:

- Put **Gemini vision models first** (required for web search anyway) and keep OpenRouter low in the chain — or out of it.
- Enable several free providers (Groq, NVIDIA, Z.ai, GitHub, …) so the gateway can spread the load; each key brings its own quota.
- Watch the gateway's free-tier budget API / response headers in the app's diagnostics console to see real consumption.
- OpenRouter's cap rises to 1,000/day once lifetime credit purchases reach $10 — only relevant if you deliberately want more OpenRouter volume.

## 2. Install FreeLLMAPI on Windows

Easiest: the **desktop `.exe` installer** from [FreeLLMAPI Releases](https://github.com/tashfeenahmed/freellmapi/releases/latest). Alternative: Docker Compose (works in PowerShell or WSL):

```powershell
git clone https://github.com/tashfeenahmed/freellmapi.git
cd freellmapi
$Bytes = New-Object Byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($Bytes)
$ENCRYPTION_KEY = -join ($Bytes | ForEach-Object { "{0:x2}" -f $_ })
"ENCRYPTION_KEY=$ENCRYPTION_KEY`nPORT=3001" | Out-File -Encoding utf8 .env
docker compose up -d
```

Open **http://localhost:3001** — the dashboard. By default it binds to `127.0.0.1` only; keep it that way (single-user gateway guarded only by the unified key). Requirements: Windows 10+ for the desktop app / Docker (Windows 7 targets are not established for the gateway).

## 3. Add keys and build the chains

1. **Keys page** — add provider keys:
   - **Google** — required for web search (grounding only exists on Gemini). This is a key for the *gateway's* Google provider route; if you cannot use any Google-family route at all, web search has nowhere to live (architecture Q1) — tell me and we pick a different search design.
   - **OpenRouter** (optional, low priority given the 50/day cap), **Groq**, **NVIDIA**, **Z.ai**, **GitHub**, etc. — free-tier vision providers for the general pool.
2. Grab the **unified API key** from the Keys page header (looks like `freellmapi-…`). This is the only key Screen Answer ever sees.
3. **Fallback Chain page** — create a named profile called **`search`** containing **only Google vision models** (e.g. Gemini 2.5/3.x vision entries), top to bottom. This is what `auto:search` routes through — it guarantees grounded requests land on a search-capable model, and an unknown/missing profile returns a clear `400` rather than silently going elsewhere.
4. Reorder the **active** chain (what plain `auto` uses) with your other vision models — remember the Vision badge: image requests only route to vision-capable models, otherwise the gateway returns `422 no_vision_model`.

### Recommended multi-model failover chain ("if one dies, the next answers")

Failover is built in: `auto` / `auto:reliable` walks the chain top to bottom and
skips anything that is disabled, has no key, or is cooling down (`exhausted`).
The first model that is **ready** serves the request. Add these models on the
**Models** page and order them like this:

| # | Model | Provider route | Why it's here |
|---|-------|----------------|---------------|
| 1 | `google/gemini-3.8-flash` (or 2.5 Flash) | Google key | Fastest free tier (80–120/4h) and the **only** route that supports `google_search` grounding |
| 2 | `google/gemini-2.5-flash` | Google key | Second Google tier — keeps search alive when tier 1 is cooling down |
| 3 | `meta/llama-4-scout-17b-16e-instruct` | Groq | Solid vision, 100/8h, no Google dependency |
| 4 | `zai/glm-4.6v-flash` | Z.ai key | Cheap fast vision, 100/3h once the key is added |
| 5 | `github/gpt-4o` | GitHub key | 50/day backup |
| 6 | `nvidia/nemotron-nano-12b-vl` | OpenRouter (NVIDIA NIM) | 60/hr if you add the OpenRouter key |
| last | anything OpenRouter | OpenRouter | **Keep last** — your tier is 50 requests/day; save it as the final fallback |

The `search` profile should be Google-only rows in the same top-to-bottom order.
Image requests never hit text-only models (vision filter), and when a row shows
`exhausted` on the dashboard it simply gets skipped — the next ready model
answers automatically. **You do not need to change anything in Screen Answer
when a provider dies.**

### Watching provider status

- **In the app** — Settings GUI → **Providers & status**. Live table of every
  model behind the gateway with status badges: `● ready` (green — serves now),
  `● exhausted` (red — cooling down), `● needs key` (orange — add the key),
  `◆ router` (blue — `auto`/profile entries). Auto-refreshes every 5 seconds.
- **On the dashboard** — the Models page shows the same statuses highlighted;
  that's where you add keys and drag chain order.

## 4. Point Screen Answer at the gateway

```powershell
$env:FREELLMAPI_API_KEY = "freellmapi-…unified key…"
python -m screenanswer
```

Or enter the endpoint/key in the Settings GUI. Defaults are already right: endpoint `http://127.0.0.1:3001/v1`, model `auto:reliable`, **web search on** (which steers requests to `auto:search`).

## 5. Verify — web search must actually work

**Smoke test through the gateway** (the same example FreeLLMAPI's docs use):

```powershell
curl http://localhost:3001/v1/chat/completions `
  -H "Authorization: Bearer freellmapi-…unified key…" `
  -H "Content-Type: application/json" `
  -d '{"model":"auto:search","messages":[{"role":"user","content":"Who won the F1 race this weekend?"}],"tools":[{"type":"function","function":{"name":"google_search","parameters":{}}}]}'
```

A current, grounded answer means search works. Then in the app: run a **time-sensitive** question on a synthetic screenshot and check the diagnostics console for `google_search grounding tool attached` and the served model line.

**Failure contract (by design):** if the `search` profile is missing or has no search-capable model, the request fails with `no_search_model` and the tray stays grey with a diagnostic message — it will *not* silently answer ungrounded.

## 6. Go-live checklist

- [ ] Gateway running on `127.0.0.1:3001` (loopback only)
- [ ] Google key added; `search` profile = Google vision models only
- [ ] Optional free-pool keys added; OpenRouter low/absent given 50/day
- [ ] Unified key in `FREELLMAPI_API_KEY`; app defaults unchanged
- [ ] Live smoke: grounded F1-style question answers correctly
- [ ] 10–20 known-answer screenshots with search on/off; record accuracy + latency + usage headers
- [ ] Only then: a bounded 80–120 question session (stop at ~40 OpenRouter calls if it is in the chain)

## 7. References

- [FreeLLMAPI install guide](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/install/01-install.md) · [REST API (routing, vision, grounding)](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/api/01-rest-api.md) · [architecture](https://github.com/tashfeenahmed/freellmapi/blob/main/docs/en/architecture/00-high-level-index.md)
- In-repo: [architecture](freellmapi-gateway-architecture.md) · [project guide](project-guide.md) · [research plan](free-model-research-action-plan.md)
