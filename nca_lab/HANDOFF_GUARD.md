# NCA Team Handoff Guard — Offline Evidence Boundary

**Status: executable offline synthetic policy exercise, NOT a live multi-agent dispatcher or production security control.**

## Purpose

NCA professional teams must be able to delegate tasks across specialized agents
without allowing one agent to acquire another agent's identity, browser session,
tenant data, budget, skills or approval authority.

The experimental guard builds on the existing `nca_lab/simulator.py`. It does
**not** replace HANTER, federated orchestrators, AI Passport, Enterprise Skills,
Guardian Core, Approval Gateway or Audit Ledger. Architecture:

`Architect → HANTER Command Center → Federated Orchestrators → NCA Teams → Bounded Execution`

There can be multiple organizations, workspaces, orchestrators and dynamically
assigned agent teams; no single unrestricted global orchestrator is introduced.

## Current executable checks

- Deny missing, inactive or unauthorized sender/receiver identities.
- Deny cross-organization and cross-workspace handoffs.
- Deny unassigned receiver capabilities and secret-classified handoffs.
- Simulate per-agent browser namespace isolation: the receiving agent may use
  only its assigned namespace, which must not equal the sender's namespace.
- Hold all nonzero estimated spending under `FREE_ONLY`.
- Hold simulated publication without an approval reference or when data is not
  public; hold simulated payment confirmation without approval and an external
  receipt reference.
- Honor the kill-switch input, reject malformed schemas and return
  deterministic audit digests of the synthetic request, registry and decision.
- Always return `real_execution_allowed: false` and `external_effects: 0`.

**Trust boundary:** the registry, claimed approvals and receipts are plain
caller-supplied test data. Their presence is NOT cryptographic verification.
The audit digest is not a signed audit record. A simulated allow must never be
used as a real permission token. Never connect this exercise to live accounts,
browsers, publishing endpoints or payments without a separate implementation,
identity attestation, independent security review and explicit Owner Approval.

## Reproduce

Python 3.11+; no dependencies, credentials or external services.

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The twelve new tests cover positive simulated handoffs and negative conditions
including org/workspace crossing, browser namespace spoofing/collision, kill
switch, spending, missing skills, forged approvals and malformed request types.
These are in-process unit tests, **not** proof of secure runtime execution.

## Competitive engineering acceptance criteria — proposed, not achieved

| Criterion | Proposed independent acceptance gate |
| --- | --- |
| Task quality | Blind, independently scored common tasks; evidence-backed outputs |
| Multi-agent collaboration | Reproducible handoff, recovery and task-completion tests |
| Browser autonomy | Per-agent isolated sessions, replay traces, no cross-agent leak |
| Security | Red-team tests for prompt injection, data exfiltration and tenant escape |
| Cost | Cost/task and work/unit measured under equal workloads |
| Reliability | 24-hour/7-day runs with uptime, failure and recovery measurements |
| Governance | AI Passport, skill-bound capabilities, Guardian, Approval and Audit |
| Scalability | Load tests with observed throughput and cost; no claim of 1B active agents |

Results must be published with fixture versions, model/provider revisions,
environment, sample size, failure counts and independent reviewer. Competing
products must be assessed legally using equally scoped public or permitted tests.
No superiority claim follows from an architectural checklist or this offline lab.

## Production gaps

1. Authenticate agent identities and bind each capability to a signed,
   short-lived AI Passport and scoped Enterprise Skills.
2. Obtain non-forgeable authorization from the actual Guardian Core and
   Approval Gateway; protect private/public and crypto ecosystem boundaries.
3. Provision real isolated browser/container resources for each active agent,
   enforce leases, teardown, network policy and complete audit trails.
4. Introduce resilient federation, state recovery, independent QA, ProofGraph
   evidence and scoped real task dispatch, first in a sandbox.
5. Benchmark quality and stability against alternatives using reproducible
   evidence rather than logos, marketing or test counts.

**No real agents were activated or trained by this change.**
