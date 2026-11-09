# NCA Sprint 016 — Signed Local Execution, Durable Queue and Stop Controls

**2026-11-02 | Architecture → Implementation → Evidence | FREE_ONLY**  
**Founder • Owner • CEO:** Alexander Nikolaevich Romaskevich (RomaskevicH).

## Delivered implementation
- [nca_control/protocol.py](../nca_control/protocol.py): validates **real Ed25519 signatures** from caller-provided public-key trust configuration, issuer `HANTER-LAB-ONLY`, audience `LOCAL_SYNTHETIC_ONLY`, 300-second maximum permit, immutable document/blueprint hashes and identifiers. Real cryptography, **demo authority only**.
- [nca_control/queue.py](../nca_control/queue.py): durable SQLite mission queue, signed permit entry point, nonce/job uniqueness, single claim token (stored as a hash), no double completion, expiry, local persisted agent/global stop and simple chained event hashes.
- [nca_control/worker.py](../nca_control/worker.py): consumes an accepted synthetic job; checks exact document hash; calls the previously built local Chromium snapshot and Ollama adapter; scores model output by deterministic rubric; rechecks the durable stop/expiry before recording the outcome.
- [nca_control/__main__.py](../nca_control/__main__.py): one opt-in **real local model** example using an in-memory ephemeral lab signer. No secrets are checked into Git; no actual Owner enrollment is performed.
- [tests/test_nca_control.py](../tests/test_nca_control.py) and [tests/test_nca_control_worker.py](../tests/test_nca_control_worker.py) cover signature tampering, foreign keys, expiration, replay across restart, single claim ownership, stop midflight, missed deadline, rejected browser evidence, low QA score and no double completion.

## Evidence and known limits

[Signed queue and worker CI run 41531406372](https://github.com/oromaskevic23-cmd/Nano-Core-Agents-Public/actions/runs/41531406372) recorded **20/20 PASS** on **Python 3.11** and **Python 3.12**. These are actual local tests of cryptographic verification and persisted queue behavior. The Chromium and LLM interfaces are **injected test doubles** in that 20-test suite.

A separate one-time [genuine local signed execution workflow](../.github/workflows/nca-control-real-once.yml) installs Chromium and a checksummed Ollama release and runs the real browser+model task. **Its actual result must be cited from a completed Actions run; creation of a workflow is not execution evidence.** Existing Sprint 015 real Chromium/Ollama proof predates this signed control bridge and cannot be silently attributed to it.

`LOCAL_QA_PASS` means only a fixed deterministic local rubric accepted the output. It is **not** a professional qualification, independently authenticated human review, real client result, signed Owner permission, proof of an owned model or enterprise Audit Ledger.

The queue is SQLite on one local host. It does not have network-scale high availability, distributed locks, cross-region atomicity, durable multi-provider failover, protected Owner authentication or a real running worker pool. The in-process local stop can block new claims and reject results but cannot forcibly interrupt external CPU inference without a separately managed process supervisor.

## Safe reproduction

Requires Python 3.11+ and `cryptography==50.0.2`:

```bash
python3 -m pip install -r nca_control/requirements.txt
python3 -m unittest discover -s tests -p 'test_nca_control*.py' -v
```

One **real** synthetic job on a machine with Ollama and Playwright/Chromium available (additional local model download and storage required):

```bash
python3 -m pip install -r nca_browser/browser-requirements.txt
python3 -m playwright install chromium
ollama pull smollm2:1.7b-instruct-q4_K_M
IMPERIAL_SIGNED_NCA_LAB=APPROVE_LOCAL_SYNTHETIC_ONLY \
    python3 -m nca_control --live --model smollm2:1.7b-instruct-q4_K_M
```

The demo generates a fresh signing key in memory, creates and signs a strictly local synthetic mission, enqueues it, executes with the **actual local** browser and model, records QA decision and prints a redacted JSON evidence manifest. No third-party websites, marketplaces, accounts, server management APIs or financial services are called.

## Architecture alignment

Architect → HANTER AI Command Center → **multiple federated domain/region orchestrators** → NCA teams → isolated workers. Keep VELION (MAX is a mode), LEGION, ORION, CRM-SOFFT, CYBER HAK, AI Passport, Enterprise Skills, Guardian Core, Approval Gateway, Audit Ledger, ProofGraph, IntentLock, Zero Trust, Public/Private Boundary, CRYPTO IMPERIAL Ecosystem Boundary and Owner Kill Switch.

IMPERIUM remains a **long-term architectural digital currency for AI agents worldwide**, not a claim of current global use or market status. No token, payment or wallet ability is granted by this sprint.

## Next verifiable gates (not completed)

1. **Protected Owner enrollment:** genuine owner key trust, challenge-based activation, rotation, revocation, signed agent-bound AI Passport. Never mistake synthetic ephemeral DEMO keys for Owner identity.
2. **Managed host worker:** privileged stop endpoint with authenticated RBAC/ABAC and measurable cancellation of the actual isolated process; IPC/network revocation and restart recovery.
3. **Independent LEGION examiner:** specialist review separate from the worker and the model, version-locked tests and verified professional certification.
4. **One read-only cloud adapter:** vault reference, authorized tenant/region scope, credentials isolated from NCA prompts, no billing or deployment writes.
5. **HANTER integration:** one real governed dispatch from the actual protected command center to a federated domain orchestrator, proof in Audit Ledger.
6. **Multi-agent team:** after one authenticated worker is proven, a 1+5 cross-city squad with strict case isolation, race/replay tests and real work only where authorized.

The objective of **one million registered NCA identities** is a long-term scalable registry goal, not one million running autonomous agents. No paid infrastructure or subscriptions are authorized.

**Build software. Verify everything.**
