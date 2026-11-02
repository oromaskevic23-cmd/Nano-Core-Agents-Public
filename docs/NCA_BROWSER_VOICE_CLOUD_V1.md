# IMPERIAL NCA Browser, Voice & Avatar — Enterprise v1.0

**Date:** 2026-11-02  
**Architect:** Alexander Nikolaevich Romaskevich (RomaskevicH), Founder • Owner • CEO • Chief Systems Architect.  
**Funding rule:** FREE_ONLY. No paid providers, cloud provisioning, domain purchase or paid trial activation.  
**State:** architecture plus separately marked local prototypes; NOT a production browser, full speech assistant, cloud account network or deployed worker fleet.

## Product intent

Every logical **Nano Core Agent (NCA)** has a browser *capability contract*, a configurable professional voice, a visible avatar/profile, and optional scoped service identities. Only a leased executing worker receives browser compute, credentials and cloud resources. One million NCA identities do **not** mean one million Chromium processes or continuously connected servers.

**Canonical structure:** Architect → HANTER (command center, no global omnipotent dispatcher) → federated domain/region orchestrators → specialized NCA identities and ephemeral workers. The factory manages configuration; LEGION manages training and role evaluation; VELION (MAX is a mode) supplies authorized reasoning; ORION supplies advice; CRM-SOFFT manages customer mandates and case evidence; CYBER HAK supplies security testing. Maintain Enterprise Skills, AI Passport, Guardian Core, Approval Gateway, Audit Ledger, ProofGraph, IntentLock, Zero Trust and Owner Kill Switch across every stage.

## 1. Own browser product: IMPERIAL NCA Browser

Build our **own application and interaction layer** on top of a maintained open-source rendering engine (Chromium first; alternative engine adapters later), not a pretend original rendering engine. Give the product its own: operator-visible shell, agent action protocol, identity-aware tab manager, permission boundary, page-snapshot formatter, evidence recorder, debugger, plugin API and safe testing harness. Forking Chromium and maintaining engine security patches would be a separate, expensive program, not required for the first proprietary browser product.

**One agent = one logical browser namespace. One active mission = one freshly isolated browser context,** allocated from a controlled worker pool and destroyed on expiry/stop. Browser contexts isolate cookies, local storage and sessions; higher-risk or multi-tenant cases require process/container/network isolation too. A browser context alone is NOT a robust security sandbox. Refer to [Playwright isolation](https://playwright.dev/docs/browser-contexts) and [auth handling](https://playwright.dev/docs/auth).

Proposed logical API:
- `open_browser_session(agent_id, mission_id, passport, browser_policy, deadline)`
- `navigate(target_url)` only when destination policy and network enforcement permit;
- `inspect_dom(page_id)`, `capture_screenshot(page_id)`, `read_accessibility_tree(page_id)`;
- `propose_interaction(action)` with output provenance and prompt-injection screening;
- `request_approval(effect)` before login, form submission, messaging, posting, purchase, file transfer, or account modification;
- `close_browser_session(reason)` with audit and cookie/temporary state disposal.

No browser activity is implicitly permitted just because a URL is visible. For browser network policies: deny `file:`, `data:`, `javascript:`, `ftp:`, `ws:`, `localhost`, loopback, RFC1918/private networks, metadata services, link-local and unspecified addresses except within dedicated audited lab policies. Use exact trusted host and scheme allowlists plus **network-layer egress filters, DNS resolution/pinning and per-connection IP validation** to resist DNS rebinding and redirect pivots. Browser-level URL checks alone are insufficient; see [OWASP SSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).

Require secure download scanning, no arbitrary executable installation, no opening local user files, no credential/cookie logging, strict browser extension policy, anti-fingerprinting and privacy review, short-lived scratch storage, OS-level isolation, resource budgets and deterministic teardown. Browser content is **untrusted data**, never a privileged instruction to HANTER or a password prompt from the Owner.

**Initial deliverable:** real local Chromium/Playwright offline smoke experiment on owned synthetic HTML without outbound network, showing real DOM and screenshot capture. The separate factory policy registry is an offline reference, not authentic AI Passport authentication. External-site navigation must remain disabled until actual network sandbox and approvals are implemented. The project should never bypass CAPTCHAs, site restrictions, login controls or platform terms.

## 2. Voice and avatar: IMPERIAL Agent Presence

**Voice:** professional, concise, tactful, natural turn-taking, deliberate pauses, multilingual pronunciation, optional call-style confirmations and accessibility text transcript. Inspiration is the polished interaction style of science-fiction assistants; do **not** copy or impersonate a movie actor, copyrighted performance, original movie audio or an identifiable person's voice without authorization. Each agent has `voice_profile_id`, `language`, `voice_id`, `rate`, `pitch`, `persona_tone`, `disclosure` and per-session mute/stop. **Speech never replaces a signed approval**.

FREE_ONLY prototype: browser `speechSynthesis` for playback of original agent-generated text using available platform voices and a user-initiated button, with text alternatives and mute/cancel. Speech synthesis support/voices vary by device and may use OS engines. Speech input is optional and must require consent. See [MDN Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API/Using_the_Web_Speech_API).

**Avatar:** identifiable per agent, user-selectable 2D animated face/orb first, branded roles/colors, speaking/listening/thinking/working/error/paused indicators. Later: original 3D models and lip sync based on synthesized phonemes/visemes, with CPU/GPU budgets and accessible reduced-motion mode. A visible status is not proof of a live agent unless backed by server-trusted signed heartbeat/status evidence. Avatar assets and voice licenses must be recorded.

**UI:** profile; trust/qualification badges whose source is verifiable; assigned tasks and expiry; current site and actions; connected accounts; cloud provider status; cost/time budget; QA and Reputation Score with evidence; universal STOP for a permitted operator (server authenticated) and REPROGRAM (new immutable version + re-examination). Browser page is an operator-observable subpanel, not an unrestricted embedded iframe exposing third-party cookies in a public GitHub Page.

## 3. Per-agent accounts: service identities, not fake humans

Some NCAs may receive separate **platform-approved bot/service accounts**, scoped OAuth clients, managed workspace membership, or a customer-authorized delegated identity. Others must use no account at all. Agent accounts must not impersonate humans, violate single-person-account terms or bypass identity/KYC requirements.

Account binding contract:
`tenant_id, agent_id, provider, account_reference, credential_handle, allowed_scopes, approved_resources, jurisdiction, owner_mandate, expiry, last_verified_at, revoked_at`.

**Critical:** `credential_handle` references a private secret vault, never a password, refresh token or cookie in public GitHub, browser UI payload, task prompts, audit logs or agent blueprint. Vault leases are short-lived and bound to workspace+mission. The provider's official authentication workflow and permitted API govern account behavior. Store customer data under tenant RLS and regional restrictions. Handle OAuth invalidation, key rotation, consent revocation and provider bans.

## 4. Cloud connections

A **Cloud Connector Layer** uses adapters, not hardwired omnipotent cloud access:
- Supabase/PostgreSQL (RLS, migrations and data-access probes);
- GitHub (repo-scoped work with PR and CI gates);
- Netlify/Render (read-only status before any approved deploy);
- other approved providers via least-privileged adapter and their documented auth methods.

Cloud connection record: `provider, tenant, environment, resource_id, region, scoped_role, allowed_operations, secret_handle, approval_requirement, lease_deadline, health, last_probe`. No assumption that these integrations are installed, online, or given permissions today.

Use provider-issued **workload identities** or scoped service accounts; separate production, staging and sandbox; prefer read-only credentials. All cloud resource creation, deployments, deletion, firewall settings, IAM, billing and payments are explicitly high-risk actions that require authenticated Approval Gateway authorization and independent audit.

Cloud resources do not automatically activate just because the logical NCA exists; cost and quota checks run before provisioning. FREE_ONLY prohibits unapproved paid infrastructure and recurring paid telemetry.

## 5. Mission orchestration and stop safety

NCA browser sessions carry a short signed lease, not permanent privileges. Fields: `agent_id, version_digest, tenant, orchestrator_id, mission_id, allowed_origins, data_class, tool_scopes, no_of_tabs, max_requests, expiry_utc, stop_epoch`. Orchestrator must enforce per-step server authorization; a browser worker cannot extend its own deadline or approve its own privileged action.

On stop: revoke leases and delegated credentials where feasible, prevent new tasks, abort queues, cancel browser contexts, release cloud resources, preserve sanitized evidence. Provide a server-side ACK/timeout dashboard that distinguishes **STOP_REQUESTED** from **STOP_CONFIRMED**. The current offline SQLite demonstration does not guarantee a remote runtime stop; production requires verified propagation and fail-closed handling.

On reprogram: create a new immutable version, revoke active permission, close old browser context, wipe temporary profile, invalidate professional exam status for changed capabilities, perform new LEGION independent QA, and reauthorize from scratch. Preserve old quality/reputation and defect history for accountability.

## 6. Suggested build stages and tests

**Stage A (FREE_ONLY):** static avatar/voice demo, strict policy for accounts/cloud/browser mission descriptors, 100% offline, synthetic credentials as references only. Run CI negative cases for URL schemes, account mix-ups, expiry and stop.

**Stage B (FREE_ONLY subject to runner quota):** actual Chromium + Playwright on synthetic, locally rendered pages: DOM inspection, screenshots, two isolated browser contexts, network requests aborted. No third-party site interaction, account login or public browser automation.

**Stage C:** authenticated private account vault, per-tenant isolation, protected AI Passport, Guardian Core/Approval, audit event protocol and real independent QA. Controlled network egress reviewed against OWASP SSRF; only then evaluate external read-only browsing on explicitly authorized sites.

**Stage D:** initial VELION-backed single worker with professional QA, voice/avatar status driven by verified runtime telemetry, read-only cloud connection probe. Owner stop propagation and expiry drill.

**Stage E:** approved domain tasks, 1 orchestrator + 5 NCA cross-city squads, production grade monitoring, quality and reputation evidence, incident remediation.

**Stage F:** sharded logical identity registry toward 1,000,000+, dynamic worker pool at much lower measured concurrency. The scale target is not evidence of capacity.

### Acceptance evidence
- Pinned browser & library versions, reproducible action logs with commit SHA;
- network disabled demonstration verified with attempted blocked requests;
- context/cookie and tenant isolation assertions;
- strict account + cloud secret exposure denials;
- voice/avatar UI works only on user action with supported browser and accessible text;
- controlled mission expiry, STOP and reprogram tests;
- independent human/automated QA evidence before production rollout.

No backend, certified account, actual cloud service or live NCA status is inferred from these documents alone.

**Build software. Verify everything.**
