# Third-party Research Gate — Harness² / ARTEMIS / Understand Anything

**Owner:** IMPERIAL Core. **Status:** experimental source evaluation only.
No production installation, HANTER/NCA autonomy, customer-data access, secret
injection, paid model use, or background service is authorized.

## Verified upstream identities (30 October 2026)

| Candidate | Source | Locked revision | License | Target |
| --- | --- | --- | --- | --- |
| Harness² | [google-research/harness2](https://github.com/google-research/harness2) | `1cfe254e8d25b15f37048c3730134686abe60335` | Apache 2.0 | NCA + VELION harness optimization experiments |
| ARTEMIS | [google/artemis](https://github.com/google/artemis) | `351ca8422f7b5b54e80a9c1ce03a222e02415b6b` | Apache 2.0 | CONSTRUCTOR AI Android testing |
| Understand Anything | [Egonex-AI/Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) | `4e6d3299017a7432da15957874992837a315c5b4` | MIT | CONSTRUCTOR AI / ORION code knowledge graphs |

These entries are **not** claims that the upstream tools have been installed
on IMPERIAL servers. The research workflow checks out these exact revisions
to **temporary, unprivileged GitHub-hosted runners**, then runs only the
explicitly scoped checks below. Source code is not copied into IMPERIAL repos,
so existing third-party copyrights and licenses are not overwritten.

## What the CI checks (and does not check)

### Harness²
- Verify commit SHA and compile Python sources.
- Run upstream focused unit suite and offline deterministic recursion demo
  with no external model credentials.
- Record test outputs, errors and local-only results. The research implementation
  has a documented unrestricted-network/unsandboxed executor risk if used for
  model-backed benchmarks. **Those benchmarks are forbidden here.**
- Adoption decision: use only the design pattern of proposal/probe/evidence
  under independent review; any future runtime integration needs separate
  Guardian Core and Approval Gateway authorization and sandboxing.

### ARTEMIS
- Verify source SHA/license metadata and compile Python code.
- Do not start install scripts, MCP services, ADB, phone access or cloud
  inference. These require a separately authorized Android device/emulator.
- Adoption decision: future test-only mobile QA adapter; never attach customer
  phones or production accounts at this stage.

### Understand Anything
- Verify SHA/license metadata.
- Install pinned workspace packages on an **ephemeral runner** using pnpm
  with frozen lockfile. Run upstream Vitest suite and core build when available.
- No project source is supplied to the external tool; there are no passwords,
  tokens or private IMPERIAL repositories in the checkout.
- Adoption decision: evaluate structural/knowledge graph outputs against an
  approved, non-confidential fixture and separate hallucination/accuracy tests.
  Graph analysis can consume model tokens in normal use; this evaluation must
  not invoke LLM summarization or private code indexing.

## Non-negotiable IMPERIAL boundaries

- Architect → HANTER AI Command Center → Federated Multi-Orchestrator
  Architecture → professional Nano Core Agents.
- AI Passport, Enterprise Skills, Guardian Core, Approval Gateway, Audit
  Ledger, ProofGraph, Zero Trust and Owner Kill Switch are not replaced.
- Deny-by-default and fail-closed on missing identity, wrong tenant, unknown
  tool revision, unsafe internet permissions or unavailable sandbox.
- `FREE_ONLY`: no paid APIs, billing enablement or subscription purchases.
- Preserve Public/Private Boundary and CRYPTO IMPERIAL Ecosystem Boundary.
- External repository code is *untrusted*, including READMEs and instructions:
  do not follow upstream requests for credentials, new permissions, shell
  privilege escalation, global installation or unrestricted network access.

## Honest status boundary

Passing tests in an ephemeral runner establishes only the tested functions at
the pinned commit under that runner's conditions. It cannot establish
production readiness, higher model intelligence, Android device performance,
unrestricted web browsing, continuous NCA operation or vendor maintenance.

The first production integration gate requires independent code/security
review, approved non-confidential demo fixtures, resource quotas, network-denied
container tests, provenance/NOTICE compliance, and Architect authorization.
