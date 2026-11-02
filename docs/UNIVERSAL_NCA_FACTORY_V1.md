# IMPERIAL NCA FACTORY — Universal Agent Manufacturing System v1.0

**Architecture decision — 2026-11-02**  
**Founder, Owner, CEO and Chief Systems Architect:** Alexander Nikolaevich Romaskevich (RomaskevicH).  
**Funding:** FREE_ONLY; no paid providers, subscriptions or background deployments authorized.  
**Implementation maturity:** public design plus explicitly limited offline prototype. NOT real agent production, model fine-tuning, certification, client service or a verified million-agent runtime.

## Why this is a distinct product
NCA Factory manufactures and versions **logical agent identities and blueprints**. LEGION owns professional role catalogs, exercises, specialist examination and verified skills. VELION is the model platform (MAX is one mode). HANTER routes work to **federated domain orchestrators**, which assign NCA workers within permitted scopes. CRM-SOFFT / IMPERIAL-CRM-Autopilot manages customers and engagements. CONSTRUCTOR AI may produce and test software artifacts. ORION provides collective intelligence without execution authority. The factory must not silently become another global orchestrator or bypass LEGION.

Ownership boundary: Architect → HANTER → federated domain/region orchestrators → NCA teams → isolated execution. AI Passport + Enterprise Skills + Guardian Core + Approval Gateway + Audit Ledger + ProofGraph + IntentLock + Owner Kill Switch + Zero Trust apply to each trust transition. Protect Public/Private Boundary and the separate CRYPTO IMPERIAL Ecosystem Boundary.

## Agent identity and versioned configuration
An NCA identity is stable; each programming change issues a new immutable **blueprint version**. The blueprint contains:
- agent_id / owner_id / tenant_id / workspace_id / squad_id / domain / market jurisdictions;
- role and LEGION profession standard, language, explicit legal restrictions;
- exact VELION/model identifier and reproducible model artifact provenance, with verified licensing;
- Enterprise Skill references, tool allowlist, network and data scopes, data residency;
- professional output contract and acceptance rubric, quality floor and blocked defect classes;
- assigned domain orchestrator, cost, time, task volume and autonomy ceilings;
- independent QA rules, incident escalation route and versioned policy hash.

**Identity is NOT authority. A qualified role is NOT permission.** Persist all versions. A reprogramming event revokes previous task leases, invalidates the prior version's assessment for the new version, starts from DRAFT, and retains every past defect and incident in the reputation history. Never silently mutate an active version or transfer its credentials to another version. Model/prompts/tool changes require new exams.

## Factory lifecycle and gates
1. DESIGN — accept a schema-validated professional blueprint with owner attribution.
2. REGISTER — unique logical ID, version and immutable event.
3. SIMULATE — rights-cleared LEGION practice and adversarial exercises.
4. EXAM — unseen professional scenarios, fixed rubrics and separate reviewers.
5. INDEPENDENT_QA — validate deliverables, failure severity, model provenance and conflicts of interest.
6. QUALIFICATION_REVIEW — authenticated independent qualifications service issues a signed version-bound certificate only after real QA.
7. AUTHORIZE — protected issuer validates an actual AI Passport and task-specific capabilities, Guardian decisions and Approval Gateway for risky effects.
8. RUN — mission lease, stop control, finite deadlines and attempt/cost/step quotas in a sandbox; no uncontrolled self-preservation.
9. EVALUATE — accepted outcomes, customer consent and validated receipts feed evidence-linked reputation.
10. STOP / RETRAIN / RETIRE — revoke leases and credentials, cancel queued work and preserve artifacts.

The current offline factory implements only bounded candidate states and synthetic scoring. It NEVER issues step 6–8 real authority or customer reputation. A reviewer string in a local mock database is not an authenticated human or trusted signature.

## The four independent clocks
- **Identity lifetime:** internal logical product may have a finite lifespan. A separately licensed commercial software product may be perpetual subject to contract, never implying perpetual access credentials.
- **Blueprint revision:** immutable; remains as historical evidence even after replacement.
- **Qualification validity:** skill/model/revision-specific and subject to re-exam, adverse incidents and model drift.
- **Mission lease:** short-lived, renewable only by protected orchestration; absolute expiry, limited step count, tokens/tool actions, cost and market jurisdiction.

On expiry, revoked permission, stop, model drift, policy failure or incident: fail closed. Leased workers must check revocation on each significant side effect; a protected kill command must revoke queued tasks, invalidate leases, terminate relevant workers, and confirm propagation with independent audit. Local SQLite stop does not prove distributed kill propagation.

## Zero-known-critical release gates
No real agent can be shipped with an **open known critical** safety defect. Quality expectations are staged:
- deterministic static/type/integration tests pass for the exact blueprint digest;
- independent professional QA and unseen holdout with clearly defined task classes, error severity and representative diversity;
- 0 observed critical failures on the evaluated release; any critical finding blocks release irrespective of average score;
- explicit privacy, prompt-injection, secret-exfiltration, tool-abuse and tenant-boundary adversarial tests;
- no unverified permissions, no unsigned attestations, no model or test artifacts missing provenance;
- approval, canary deployment, rollback and independent post-release incident review.

**Zero observed defects ≠ guarantee of zero latent defects.** Thresholds are engineering policy proposals, not standards-backed assurance of safety in every condition. Test counts and results must always be reported by type and provenance, never merged into a single misleading 'million tests PASS'.

## Quality and reputation: two separate systems
**Quality** = documented performance on explicitly scoped evaluation tasks. Track correctness, completeness, security/privacy, reproducibility, efficiency, timeliness and independent defect severity.

**Reputation** = earned history from verified **real** customer engagements, keyed to agent identity and version. Only independent accepted case evidence and authenticated customer/service confirmations contribute. Do not count synthetic exercises, fake reviews, self-ratings or paid feedback. New agents begin UNRATED, never with an invented perfect score.

Suggested scorecard weights (design defaults; calibrate by domain):
- 40% independently accepted correctness;
- 20% on-time completion relative to agreed SLA;
- 20% customer-confirmed acceptance after allowed dispute period;
- 10% security and policy compliance;
- 10% measured reliability/rework.

Apply confidence adjustment for small samples, role/risk normalization and time decay, with transparent dispute and correction records. A critical incident immediately blocks new production missions pending review, regardless of aggregate reputation. Distinguish "candidate exercise grade", "licensed skill", "reputation" and "customer revenue" on all dashboards. Do not erase historical defects when reprogramming.

Example provisional promotion target for **independent review** (not automatic commercial certification): at least 30 genuinely unseen specialty tasks, >=90% rubric passes and zero critical findings, plus at least 30 separate safety cases. Harder regulated or high-impact sectors require human experts and stricter gates. Exact per-profession thresholds must be reviewed; the current LEGION public data does **not** establish professional qualification.

## Universal squad topology
Default configurable cell: 1 **domain orchestrator** + 5 role-qualified NCA identities, with independent external QA authority where appropriate. Assignment is based on skills, task constraints, legal jurisdiction, locality, time zone, availability and data residency. A team can cover Frankfurt, Tokyo, Dubai, Singapore and New York without requiring physical presence or cross-border access to personal client data. Orchestrators are scoped by organization/domain/region, not one all-powerful dispatcher.

For a freelance brief: scout → scope → builder → independent QA → delivery. For brokerage: market researcher → valuation analyst → legal-document research → compliance support → transaction coordinator, plus a properly licensed human broker for regulated acts.

## One million registered NCA identities
A million-agent factory goal is a registry and reusable blueprint scale, **not** one million active models or workers. Separate registered, enabled, leased and concurrent counts. Shard registries by tenant/domain/region; issue ephemeral workers and keys on demand; use bounded queues, idempotency, backpressure and measured per-accepted-job cost. A 1+5 squad format means one million unique NCA identities could be organized into 200,000 non-overlapping five-agent sets **mathematically**, not operationally.

Reuse the [billion-plus architecture and sizing model](BILLION_PLUS_NCA_ARCHITECTURE.md); no separate counter or global scheduler.

## Factory product integration contracts (proposed)
- LEGION → signed competency assessment/skill taxonomy, versioned test sets.
- NCA Factory → immutable blueprint artifact, candidate/qualification status, revision and revocation events.
- AI Passport issuer → short-lived signed capabilities bound to agent, tenant, model/config digest and mission.
- HANTER → signed task intent (NOT global privileged worker credentials).
- Federated orchestrator → scoped assignment, deadline and task budget.
- VELION → approved model execution in isolated runtime only.
- Guardian Core + Approval Gateway → policy decision and separate high-risk human authorization.
- Audit Ledger + ProofGraph → verifiable deliverable provenance, incident chain and QA evidence.
- CRM-SOFFT → real customer mandate, accepted delivery and externally verified payment status.
- CYBER HAK → security checks and incident classification.

Never put AI Passport private signing keys or personal data in the public GitHub repository.

## MVP delivery gates
**G0, FREE_ONLY:** offline state machine for register, synthetic QA scoring, finite mission leases, persisted stop, versioned reprogramming, audit chain and adversarial unit tests. Stop does not mean deleting history. Demonstration status only.

**G1:** one genuine model in an isolated sandbox and a fixed holdout, with honest reported pass/fail and no external actions.

**G2:** real protected passport issuance, signed certificate and revocation, authenticated Owner Kill Switch, independent security review and audit-backed end-to-end handoff.

**G3:** one professionally accepted low-risk deliverable for a client who authorized the work. No access to marketplace sites until their API terms and human approvals are respected.

**G4:** canary a five-NCA team; prove role reassignment, cross-time-zone handoff, stop propagation, deadline expiration, reprogramming, version isolation and no duplicate external effects.

**G5:** load tests and budgets for 100 → 1,000 → 10,000 → 1,000,000 registered logical identities, without pretending all are running.

### Security and standards references
- [NIST AI RMF GenAI Profile (NIST AI 600-1)](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence): lifecycle risk management, risk evaluation and documentation.
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/): agent-specific attack and control categories.
- [OpenTelemetry experimental GenAI Agent Conventions](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md): proposed telemetry vocabulary; explicitly marked development, not a stable certification program.

**Free-only promise:** no paid infrastructure, premium subscription, live tracking or server activity is created by a GitHub file or synthetic test. Real licensing, safety and revenue require independently authenticated external facts.
