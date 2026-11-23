# NCA Sprint 019 — Fail-Closed Registry Integrity Gate

**Date:** 2026-11-23  
**Architect / Final Architectural Decision Authority:** Alexander Nikolaevich Romaskevich · Founder · Owner · CEO  
**Implementation:** isolated GitHub branch; offline synthetic NCA Factory only  
**Boundaries:** FREE_ONLY · Architecture → Implementation → Verification → Evidence · Zero Trust

## Problem

Before this sprint, `Factory.audit_valid()` checked only the chained hashes in the `audit` table. Mutating a live NCA record, editing its stored revision, or forging an `OFFLINE_CANDIDATE` state directly in SQLite could leave that audit chain structurally valid. Other operations trusted the current `agents` row without reconciling its source blueprint, current revision or prerequisite test scores.

This is a data-integrity defect in the **offline reference**, not proof of a live security compromise.

## Implemented local guards

1. **Source digest:** the current blueprint must be valid canonical JSON under the existing blueprint schema, and SHA-256 must match its stored digest.
2. **Revision binding:** the active `agent_id/version` must have an exact matching source and digest in the immutable-history `revisions` table.
3. **Revision continuity:** the number of recorded revisions must match the current monotonic version. This detects simple deletion of historical versions from the local database.
4. **Qualification gating:** `OFFLINE_CANDIDATE` and `MOCK_ACTIVE` states must still pass the existing mock exam thresholds (at least five cases, mean ≥90, minimum ≥80, zero critical defects). Re-check on each row use so that editing an assessment after promotion cannot leave the local mock lease effective.
5. **Audit cross-check:** `audit_valid()` additionally checks all currently registered agents, rather than asserting that event hashes alone prove registry health. A mismatch returns `False`; reads and lifecycle operations raise `REGISTRY_INTEGRITY_FAILED`.

All checks are done inside the existing SQLite transaction. These changes neither create a real worker nor expand permissions.

## Regression coverage

Six new adversarial unit tests:

- Tampered live blueprint blocks inspect and subsequent revision changes.
- Modified current revision digest blocks exam startup.
- Deleted revision history invalidates the active agent record.
- Forged offline qualification cannot open a mock mission.
- Degraded exam evidence after qualification blocks a mock step.
- Valid revised and stopped agents retain consistent audit state.

The existing tests also cover tenant isolation and the persistent stop introduced in Sprint 018.

### CI acceptance command

```bash
python3 -m compileall -q nca_factory tests/test_nca_factory.py
python3 -m unittest discover -s tests -p 'test_nca_factory.py' -v
python3 -m nca_factory
```

GitHub Actions `NCA Factory | Offline release gate` runs on Python 3.11 and 3.12. **This document is not evidence of test PASS**: cite the actual workflow runs and hashes after completion.

## Security limitations and verification scope

This detects **simple local drift and tampering**, not sophisticated adversaries controlling the entire SQLite database. A privileged attacker can rewrite the registry, revisions, assessments and event hashes together. The audit table has **no independent signed checkpoint**, protected root of trust, external witness or immutable storage. It is not the enterprise Audit Ledger and must not be described as tamper-proof.

The mock exams do not constitute independent LEGION professional certification. No Owner-controlled release channel, authenticated AI Passport, Guardian Core remote policy enforcement, Approval Gateway signature, production stop relay, federated dispatch service, commercial authority, real-time Nano Core Agent fleet, or autonomous execution is delivered by this sprint.

Canonical architecture is unchanged:

Architect → HANTER (AI Command Center) → federated domain/region orchestrators → bounded professional Nano Core Agent teams → verified execution.

AI Passport, Enterprise Skills, Guardian Core, Approval Gateway, Audit Ledger, ProofGraph, IntentLock, Owner Kill Switch, Zero Trust, Public/Private Boundary and CRYPTO IMPERIAL Ecosystem Boundary remain mandatory for future production integration.

The architecture supports multiple organizations, roles and dynamic team sizes without claiming current fleet scale. Any mention of IMPERIUM refers only to the long-term architectural digital currency envisioned for AI agents worldwide, not present worldwide usage or market status.

## Release gates

- Verify the focused factory suite and offline demo on Python 3.11/3.12 against the exact PR head.
- Confirm enterprise, provenance and English docs workflow results.
- Compare file scope: `nca_factory/factory.py`, `tests/test_nca_factory.py`, and this documentation only.
- The open supervised worker PR #13 remains independent; no automatic merge or production deployment.
