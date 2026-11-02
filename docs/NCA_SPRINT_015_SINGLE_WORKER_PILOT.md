# Sprint 015 — Single NCA: Chromium × VELION Provider Port × QA

**Date:** 2026-11-02  
**Author / Final Architectural Decision Authority:** Alexander Nikolaevich Romaskevich (RomaskevicH).  
**Funding:** FREE_ONLY. **Status:** integration implementation and CI validation; local real inference is separately opt-in. No live customer, paid agent, real AI Passport or production authorization is claimed.

## Scope and architectural choice

A bounded **one-agent** local experiment unifies NCA Factory, Chromium, an Ollama **third-party model** behind the future VELION provider port, a deterministic independent-output QA rule, a mission lease and stop/reprogram checks. Model inference is not model training; interfacing with Ollama is not proof that VELION proprietary model weights exist.

**Canonical federation:** Architect → HANTER → **multiple domain orchestrators** → NCA → isolated worker. Keep ORION, LEGION, VELION, CRM-SOFFT, CYBER HAK, AI Passport, Enterprise Skills, Guardian Core, Approval Gateway, Audit Ledger, ProofGraph, IntentLock, Owner Kill Switch, Zero Trust, Public/Private Boundary and CRYPTO IMPERIAL Ecosystem Boundary. Do not elevate an ordinary prompt into authority or connect accounts to the public browser demo.

## Implemented components
- `nca_runtime/ollama_adapter.py`: one JSON-mode local `POST http://127.0.0.1:11434/api/chat` request, `stream: false`, `tools` omitted, fixed loopback endpoint, bounded bytes/time, no cookies or credentials. Uses approved model name from the CLI; it cannot choose an external endpoint.
- `nca_runtime/browser_snapshot.py`: actual Chromium with a new isolated browser context, disabled page JavaScript, all network requests aborted in the browser, only supplied locally authored HTML, screenshot SHA-256 and DOM heading/text.
- `nca_runtime/pilot.py`: checks the exact factory blueprint, bound mission, lease and step count; consumes a local step before inference; rejects stale, stopped, expired or reprogrammed output; produces a redacted evidence manifest, not browser/tool actions.
- `nca_runtime/__main__.py`: opt-in CLI. The five starting exam grades are **explicit mock fixtures**, not independent QA or professional qualifications.
- `tests/test_nca_runtime.py`: injected-mock tests of safety/contract and deterministic QA. These tests do not execute the actual model. Real Chromium is separately validated by the browser workflow.
- `nca_browser/web`: original voice/avatar interface uses user-initiated device speech. This pilot's runtime report is not yet wired to verified live avatar status or remote control.

## Exact local procedure

**Prerequisites:** personally owned/authorized machine, Python 3.11+, already available Ollama server at `127.0.0.1:11434`, a locally downloaded model whose terms allow use, plus Playwright/Chromium downloaded from their official source. No cloud account is needed.

Run from repo root:

```bash
python3 -m pip install -r nca_browser/browser-requirements.txt
python3 -m playwright install chromium
ollama pull smollm2:1.7b-instruct-q4_K_M
IMPERIAL_NCA_LOCAL_LLM=ALLOW_LOCAL_SYNTHETIC_INFERENCE python3 -m nca_runtime --live --model smollm2:1.7b-instruct-q4_K_M
```

**Note:** `ollama pull` requires an Internet download and local disk. This is a no-subscription local option, not a guarantee that downloads, devices, GitHub runners or hosting are cost-free. Verify model availability and license before use.

**Output:** one JSON manifest with blueprint SHA, page and screenshot SHA, model request/response SHA, simple QA result, stop/expiry state and `production_authorized: false`. The CLI does not print the model's entire response or credentials. No job is created on any third-party website, no cloud server is provisioned and no payment is made.

## Acceptance criteria (per source)
| Gate | Observable acceptance | Scope |
| --- | --- | --- |
| P1 | 1 registered agent bound to exactly one blueprint revision | SQLite offline lab |
| P2 | 1 active mock lease; wrong mission, expiry, quota and replay rejected | Offline lab |
| P3 | 1 real locally authored page rendered by Chromium, screenshot hash captured | Local machine/CI browser |
| P4 | Local Ollama response parsed as JSON; remote URLs/tools not called | Opt-in real model only |
| P5 | Deterministic QA matches visible H1 and rejects unsupported claims | Basic output rubric |
| P6 | Local stop or reprogram during inference rejects completion | Local lab |
| P7 | No paid services, real account, commercial platform, payment or production grants | Static fail-closed boundary |
| P8 | CI and any real-model run IDs linked; failed results remain visible | Evidence review |

**Evidence policy:** CI mock tests are not real model calls. The separately verified Chromium smoke test is actual browser execution, but not hardened network isolation. Model QA is not an independently authenticated human review, professional exam or comprehensive prompt-injection evaluation. The local SQLite hash chain is not a signed remote Audit Ledger.

## Context7 verified APIs

- [Ollama official API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md) — local POST /api/chat, stream false, messages, format=json and keep_alive options.
- [Playwright BrowserContext reference](https://github.com/microsoft/playwright/blob/main/docs/src/api/class-browsercontext.md) — isolated contexts and context.route interception.

## Remaining production gates

1. Real Owner Ed25519 key enrollment, trusted issuer, signed/version-bound AI Passport and protected stop revocation.
2. One permanently managed isolated worker with explicit runtime cancellation; reliable network-level egress policy.
3. Separate LEGION professional exams on genuinely unseen briefs, expert QA and signed reproducible artifacts.
4. Secure account vault, explicit service identities and read-only cloud adapter, tenant boundaries and data residency.
5. VELION model/router provenance; benchmark performance against correct model versions. No claim of owning third-party weights.
6. Verified UI event stream for avatar/voice based on actual runtime, avoiding false ONLINE statuses.
7. Only after the above: one client-authorized low-risk pilot, and then 1+5 NCA squad with federated orchestrator.

**Deployment does not equal evidence. Build software. Verify everything.**
