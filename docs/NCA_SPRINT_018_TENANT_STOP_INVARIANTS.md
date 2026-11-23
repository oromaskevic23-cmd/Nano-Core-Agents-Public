# NCA Sprint 018 — Tenant Isolation and Stop-Preserving Agent Revisions

**Date:** 2026-11-23  
**Authority:** Alexander Nikolaevich Romaskevich · Founder · Owner · CEO · Final Architectural Authority  
**Status:** IMPLEMENTED IN AN ISOLATED BRANCH; CI and independent release approval required  
**Mode:** REAL CODE · FREE_ONLY · ZERO TRUST · EVIDENCE FIRST · NO PRODUCTION AUTHORIZATION

## 1. Engineering objective

Raise the safety baseline for Nano Core Agents by ensuring that an agent's logical identity cannot be silently moved between organizations, and that editing a blueprint never cancels an emergency stop.

The existing public `nca_factory` is an **offline synthetic lifecycle reference**, not a running multi-agent commercial service. This change hardens that reference without claiming deployment, a real AI Passport, authenticated Owner recovery, a connected HANTER, autonomous orchestration or production certification.

## 2. Verified baseline and ownership boundaries

- Canonical chain: **Architect → HANTER (AI Command Center) → federated domain/region orchestrators → professional Nano Core Agent teams → bounded isolated workers**.
- Other domain boundaries remain separate: VELION intelligence; LEGION independent skill examination; Guardian Core; Approval Gateway; Audit Ledger; AI Passport; Enterprise Skills; IntentLock; ProofGraph; Owner Kill Switch; Zero Trust; Public/Private Boundary and CRYPTO IMPERIAL Ecosystem Boundary.
- NCA Factory uses a versioned SQLite blueprint reference, mock exams and mock leases. It must not mint genuine credentials or claim actual Owner consent.
- The repository also has an existing [PR #13](https://github.com/oromaskevic23-cmd/Nano-Core-Agents-Public/pull/13) for a supervised single-host worker and recovery. **Do not duplicate or silently merge that work.** Its lease controls require separate review.

## 3. Security gaps addressed

### A. Cross-tenant identity reassignment

Before Sprint 018, `Factory.reprogram(agent_id, blueprint)` could accept a different `tenant` in a revision under the same `agent_id`.

**New invariant:** `tenant` is immutable for the lifetime of a logical agent identity. A cross-tenant revision raises `TENANT_BOUNDARY_CHANGE_FORBIDDEN` before changes to the database. A different tenant must create a **new agent identity** and separately pass the lifecycle and governance controls. Moving the existing identity or its revision history is not implemented.

### B. Emergency stop unintentionally cleared by reprogramming

Previously `reprogram` deleted an agent's row from `controls`, and `inspect` therefore reported DRAFT after an emergency stop. This let local code resume mock examination simply by changing a blueprint.

**New invariant:** `reprogram` leaves the stop record intact. Revision history still advances and the internal revision is DRAFT, but the effective public state remains STOPPED, the prior mock lease is removed, and further `start_exam` and mock execution are denied. The offline example **does not provide an Owner-authenticated resume**, so a stopped identity stays stopped. A future recovery channel must be designed and separately authorized rather than introduced as an unsafe default.

### C. No-op version minting

Before Sprint 018, resubmitting an identical blueprint could create another version without a substantive change.

**New invariant:** identical blueprint digest raises `UNCHANGED_BLUEPRINT`; no revision, lease, stop, or audit changes are committed.

### D. Traceable revision evidence

Accepted `REPROGRAM` audit entries now include original `tenant`, `previous_digest`, `digest`, `from_version`, and `to_version`. The local hash-chain only detects certain tampering and is **not** a signed enterprise Audit Ledger.

## 4. Explicit state table

| Starting state | Requested operation | Result | Production authority |
| --- | --- | --- | --- |
| DRAFT, tenant A | same tenant + different role | version increments, state DRAFT | Never |
| MOCK_ACTIVE, tenant A | same tenant + different blueprint | mock lease revoked, revision DRAFT | Never |
| STOPPED, tenant A | same tenant + different blueprint | revision recorded, effective state STOPPED | Never |
| Any, tenant A | change tenant to B | denied atomically | Never |
| Any | same blueprint digest | denied atomically | Never |
| GLOBAL STOP | any reprogramming | denied atomically | Never |

## 5. Regression acceptance

The focused `tests/test_nca_factory.py` suite tests:
1. A stop persists through version increment, fresh `Factory(db)` instance, and attempted new examination/lease.
2. A cross-tenant reprogram cannot change version, digest, the revision count, or the audit count.
3. A no-op reprogram cannot mint an additional version.
4. A successful same-tenant version transition writes the previous/new digests, tenant, and version information into the local audit event.
5. Existing exam score, defects, quota, replay, global stop and local lifecycle tests remain applicable.

**Evidence rule:** source commits, test discovery and workflow results must be cited by exact SHA/run. This document does not declare any test PASS until an actual invocation reports it.

Suggested local command, using Python 3.11+ and standard library only:

```bash
python3 -m compileall -q nca_factory tests/test_nca_factory.py
python3 -m unittest discover -s tests -p 'test_nca_factory.py' -v
python3 -m nca_factory
```

The existing `NCA Factory | Offline release gate` workflow automatically covers Python 3.11 and 3.12 on PRs. Treat a skipped, failed or unexecuted workflow as **not verified**.

## 6. Beyond this sprint — not implemented

Before genuine Enterprise operation, deliver an authenticated per-tenant AI Passport issuer and revocation, independent Owner recovery, signed approval policy, cross-domain orchestrator dispatch, protected credentials, independent LEGION QA, real Audit Ledger append-only guarantees, sandbox/runtime isolation, persistent process supervision and owner-authorized kill propagation. No current code change here proves any of those.

The architecture is prepared for many organizational structures and dynamically sized NCA teams; it is **not** a statement that a million agents or a global network is operating.

**IMPERIUM**, if mentioned elsewhere, remains a long-term architectural digital currency intended for AI agents worldwide, with no assertion of current global usage, exchange listing or market status.

**Release policy:** do not merge into `main` until the focused tests pass, the open worker PR's compatibility is reviewed, and the Architect's governance rules are respected.
