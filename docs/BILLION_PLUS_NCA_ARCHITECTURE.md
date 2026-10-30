# IMPERIAL Core — Billion-Plus NCA Future-Scale Architecture

**Status:** FUTURE TARGET / DESIGN AND CAPACITY ARITHMETIC ONLY — NOT A DEPLOYED SYSTEM.
**Owner and Final Architectural Decision Authority:** Alexander Nikolaevich Romaskevich (RomaskevicH).
**Scope:** federated universal Nano Core Agents (NCA) across multiple organizations, professions, runtime domains and regions.
**Date:** 2026-10-31.
**Funding rule:** FREE_ONLY; no infrastructure purchase, deployment, cloud upgrade, recurring monitoring or runtime activation is authorized by this document.

## 1. Design target and meanings

Target **1,000,000,000+ registered NCA identities** over the long term. This is a *logical-address-space and partitionability target*, **not** evidence of one billion deployed, concurrent, paid, trained or autonomous agents. Track four different numbers separately:

1. **Registered:** unique logical agent identities in the canonical directory.
2. **Enabled:** authorized identities currently eligible to receive jobs.
3. **Active:** identities with a valid worker lease or ongoing task.
4. **Concurrent executions:** actual isolated worker processes, containers, browser sessions or model calls.

No registered identity inherently consumes a continuously running container or browser. A distinct browser **security namespace** per active NCA is required for browser tasks; physical resources may be allocated just in time, with isolation and teardown verified.

## 2. Canonical authority and federation

Architect / Owner and Final Architectural Decision Authority
→ **HANTER** (AI Command Center; intake, policy-bound command routing and mission visibility)
→ **Federated Domain Orchestrators** (many; partitioned by organizational structure, profession, geography and trust boundary)
→ **Professional NCA Teams**
→ **Isolated, leased NCA Workers** (bounded actions, independent QA and evidence).

**ORION** supplies collective intelligence, cross-team synthesis and recommendations; it cannot bypass an orchestrator or promote advice into execution authority.
**LEGION** provides specialist roles. **VELION** is the model platform; MAX is a mode, not its product name.
**Guardian Core**, **Approval Gateway**, **AI Passport**, **Enterprise Skills**, **Audit Ledger**, **ProofGraph**, **IntentLock**, **Owner Kill Switch** and **Zero Trust** are mandatory control requirements. No single global execution orchestrator, universal service account or blanket agent token may be introduced.

## 3. Control plane, data plane, trust boundaries

- **Federation directory:** resolves organization / workspace / domain / shard to the responsible authorized orchestrator. It does not hold universal execution credentials.
- **Agent registry:** logical NCA identity, tenant, immutable identifier, profile version, permitted skill references, lifecycle status, region residency and revocation marker. Secrets and private passport keys are not stored in a public registry.
- **AI Passport:** cryptographically verifiable short-lived identity and context-bound capability; rotation, revocation, issuer trust, audience, expiry and replay protection are required before production. A simulation boolean is never a valid Passport.
- **Enterprise Skills:** versioned, allowlisted, minimally privileged capabilities, limited to the current tenant, workspace, task and resource.
- **Task plane:** durable domain-scoped inbox/outbox, versioned task envelope, idempotency key, correlation ID, leased ownership, expiry, bounded retries, dead-letter quarantine and cancellation.
- **Runtime plane:** pools of ephemeral NCA workers with per-task secrets, network policies, sandbox isolation, isolated browser state, resource limits and enforced expiry.
- **Approval Gateway:** authorizes high-risk external side effects. Guardian Core screens policy. Fail closed on timeout, stale approval, revocation, kill switch or missing evidence. The Owner's command defines intent, not an exception to policy or law.
- **Audit Ledger and ProofGraph:** retain verifiable task provenance, decisions, approvals, test artifacts and independent QA; integrity, retention and tenant access are separate concerns.
- **Public / Private Boundary:** public GitHub designs cannot dispatch private jobs or reveal private data.
- **CRYPTO IMPERIAL Ecosystem Boundary:** no automatic token transaction, exchange listing, trading, custody, payment confirmation or financial action. External receipts and explicit Owner approval are separate preconditions where relevant.

## 4. Scaling principles

### Partition first

Shard by tenant/workspace and domain, then by stable hashed agent ID within assigned region. Keep tenancy/security boundaries **stronger** than raw throughput optimization. Support placement rules and controlled migration with auditable ownership transfer. Do not assume one PostgreSQL primary or Supabase project can serve the entire eventual fleet.

### Separate cold registry from hot execution

Cold identities belong to a distributed directory/registry. Hot leases, scheduling, streams, status and ephemeral browser resources belong to appropriately scoped runtime services. Do not poll or persist a heartbeat for every dormant identity; use aggregate health reporting where meaningful.

### Delivery semantics

Assume at-least-once event delivery and possible duplicates or reordering. Require durable deduplication keyed by tenant + job + operation, transactional outbox/inbox, idempotent external-effect adapters and receipt reconciliation. **Do not claim exactly-once execution** across network and third-party API boundaries.

### Failure containment

Domain-level budgets and quotas, token buckets, admission control, fair queueing, backpressure, circuit breakers, graceful draining, recovery of expired leases and dead-letter review. A compromised or overloaded domain must not gain access to another domain. The Owner Kill Switch must be enforceable across all active domains, with measurable propagation and a deny-by-default failure posture.

### Federation governance

HANTER handles mission intent and visibility; domain orchestrators make scoped scheduling decisions, not global unrestricted execution decisions. Signed policy versions, authorized handoff contracts, audit traces and conflict resolution must be validated before cross-domain delegation. An agent cannot grant itself permissions, elevate its role, change payout, forge approvals or impersonate the Architect.

## 5. Hypothetical sizing model (NOT measured performance)

The adjacent offline script is **nca_lab/capacity_model.py**. Default assumptions are design inputs, not observations:

- Registered identities: 1,000,000,000.
- Active: 1,000,000 (0.1% of registered).
- Two task starts per active identity per day.
- One heartbeat *message* per active identity per 300 seconds, with no assumption all messages become database writes.
- Five audit events per task; 512 logical registry bytes/identity; replication factor three.
- Steady-state averages only. Bursts, indexes, storage engine amplification, quorum protocols, backups, replication transport, data retention and actual bills are not included.

| Illustrative active NCA | Task starts/s | Heartbeats/s at 300 s |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 10,000 | 0.2315 | 33.3333 |
| 1,000,000 | 23.1481 | 3,333.3333 |
| 100,000,000 | 2,314.8148 | 333,333.3333 |
| 1,000,000,000 | 23,148.1481 | 3,333,333.3333 |

Arithmetic is active_agents × 2 / 86,400 for task starts per second, and active_agents / 300 for heartbeat messages per second. 1B × 512 B = **512 GB** raw logical registry data; factor-three replicas = **1.536 TB before all overhead**. These figures are not hardware/storage quotes or capacity claims.

**Operational consequence:** the heartbeat stream alone can become enormous. Before any large deployment, replace naive per-agent periodic writes with scoped leases, event-driven updates and aggregated telemetry; measure cost and data retention.

## 6. Evidence-gated roadmap

**Stage 0 — Current:** documented canonical architecture, offline synthetic NCA handoff guard and this capacity arithmetic; no evidence of a deployed billion-agent platform.

**Stage 1 — Small authorized pilot:** deploy 1–10 sandbox workers and a single scoped domain coordinator only after separate Owner approval, authenticated AI Passport, protected secrets, Guardian Core, Approval Gateway, Audit Ledger and independent QA. Record signed evidence; no customer effects.

**Stage 2 — Controlled federation:** at least two independent domain orchestrators, tenant boundaries, recoverable task queue, expiration/replay/idempotency testing, chaos tests and measured rollback. Use only approved funding and resource budgets.

**Stage 3 — Partitioning tests:** generate synthetic registry datasets with independently checked totals and representative skew. Benchmark growing registry sizes **without activating all identities**. Report throughput, p50/p95/p99 latency, SLO failures, memory, storage, network, cloud spend and shard movement.

**Stage 4 — Large-scale production readiness:** separately prove recovery, tenant isolation, security, audit completeness, cross-region consistency, operational support and financially sustainable infrastructure at measured intermediate scales. Billion-plus readiness is not achieved by passing an arithmetic unit test.

## 7. Mandatory acceptance gates before a scale claim

- Independent authorization and adversarial testing (passport forging, stale revocation, prompt injection, credential leakage, tenant escape).
- Replay-safe task handoff and external-effect idempotency proven under failures; isolated browsers and worker lifecycle teardown.
- Measured peak load, not just averages; documented bottlenecks, shard skew, capacity margins, degraded modes and recovery objectives.
- Reproducible run manifest: code SHA, dataset generator, seed, versions, runtime topology, resource count, scenario, error count, cost and independently reviewed test results.
- No unapproved paid infrastructure or hidden recurring task. Explicit Owner Approval and independent QA precede every production activation.
- A deployment remains **NOT VERIFIED** until its corresponding release and operational evidence exists.

## 8. Reference implementation boundary

The Python calculator and its tests are **offline, pure arithmetic**. The repository's existing synthetic handoff exercises remain separate. None of these artifacts trains a model, provisions a server, dispatches work, runs a live NCA, attests a cryptographic passport, creates a real Audit Ledger or proves billion-scale throughput.

**Licensing:** the existing repository LICENSE, provenance and third-party notices continue to apply; this document does not grant new rights. The planned digital currency **IMPERIUM** is a long-term architectural concept for AI agents worldwide, not a claim of current worldwide use or exchange status.

**Build software. Verify everything.**
