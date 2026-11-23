# One supervised NCA lab worker

This implements a **single-host, opt-in lab process** for the existing signed synthetic NCA queue. It is not an authenticated Owner AI Passport, a production HANTER connection, an independent human examiner, a commercial worker, a hosted service or proof of continuous availability.

The loop checks local dependencies, claims a permitted synthetic job, supervises one child, records a minimal local heartbeat and waits for the next job. It cannot browse the internet, send messages, access customer accounts or make payments. The browser is used only for the repository's fixed synthetic HTML; a third-party local Ollama model receives text without tools. The bounded lab permit lasts at most 300 seconds.

## Recovery and safety

- Each claim has an expiry no later than the signed permit. A running worker renews its lease; a stalled claim can be recovered at most twice while the permit remains valid. The old claim token cannot complete the recovered job.
- Stop and expiry are checked at claim, before browser work, before model inference and before completion. A local stop causes the supervisor to terminate the child. On POSIX it also signals that child's process group; this is best effort, not a host security sandbox. An already received request may continue running inside a separately hosted Ollama process.
- Worker heartbeat is an unauthenticated local SQLite record. It can reveal an idle, waiting, executing, stopped or stale lab process; it does not prove live inference, identity, independence, uptime or production readiness. Hash-chained local events are not tamper-proof against an administrator.
- Stop/resume controls are **local filesystem controls**, not a verified remote Owner Kill Switch. Resuming clears the stop for future jobs and never revives jobs already marked `STOPPED`.
- Schema migration preserves an older SQLite queue. A job already claimed by an older version has no trustworthy lease; it is left for manual review until its original permit expires. Stop all old workers before upgrading. Never point this lab at a production database.
- Automatic recovery is safe only within this fixed synthetic, no-external-effects scope. Fencing prevents stale completion but cannot prove exactly-once execution or stop a model server that already received a request. Do not reuse this retry mechanism for customer actions without stronger isolation, idempotency and independently verified authorization.

## Local demonstration

Requirements: Python 3.11+, the existing `nca_control/requirements.txt`, Playwright and Chromium from `nca_browser/browser-requirements.txt`, and an independently installed Ollama instance with an authorized model. Model weights and their licenses must be independently verified. No paid API is needed for the documented local lab, but installation, storage and compute are the operator's responsibility.

Use a private persistent directory and a trusted host. From the repository checkout:

```sh
mkdir -m 700 -p /path/to/private/nca-lab
export IMPERIAL_NCA_ALWAYS_ON_LAB=ALLOW_LOCAL_SYNTHETIC_ONLY
python3 -m nca_control.always_on --run-lab \
  --database /path/to/private/nca-lab/queue.sqlite --worker-id nca-local-worker-1
```

In a second terminal, check that the local status is `IDLE` before submitting: if dependencies are unavailable, status is `WAITING_DEPENDENCIES` and a short-lived permit may expire without execution.

```sh
python3 -m nca_control.local_admin --database /path/to/private/nca-lab/queue.sqlite status
python3 -m nca_control.lab_submit --submit-lab --database /path/to/private/nca-lab/queue.sqlite
python3 -m nca_control.local_admin --database /path/to/private/nca-lab/queue.sqlite job --job-id '<job_id from submission>'
```

`lab_submit` signs only the fixed fixture with a newly generated **ephemeral lab key**, verifies it when submitting, and discards the key. This is not an Owner credential. It produces no real customer order or payment. Inspect the job and console output to distinguish `LOCAL_QA_PASS`, `LOCAL_QA_FAIL`, expiry and retry exhaustion; the deterministic rubric is not independent expert QA.

Local emergency stop and resume for future work:

```sh
python3 -m nca_control.local_admin --database /path/to/private/nca-lab/queue.sqlite stop --scope global --subject '*' --reason 'local stop'
python3 -m nca_control.local_admin --database /path/to/private/nca-lab/queue.sqlite resume --scope global --subject '*'
```

`ops/nca-always-on-lab.service.example` is an **uninstalled** Linux systemd example. Paths, service account, browser sandbox compatibility, local model connectivity, persistence, restart policy, backups and OS permissions must be reviewed and tested on the actual host. A sample unit does not provision a host or prove 24/7 operation.

The [real-cycle workflow](../.github/workflows/nca-always-on-real-once.yml) uses an ephemeral GitHub runner, a checksum-pinned Ollama executable, a separately downloaded third-party model and real Chromium. It exercises one lab job and graceful shutdown; examine the actual workflow run before claiming that this real inference succeeded. A passing run still does not establish continuous hosting, model-weight authenticity, Owner credentials or customer authorization.

## Reference and limits

The user-supplied image says “harvey”, “FREE” and “MIT” but does not identify an owner. A plausible public reference is [ethanplusai/harvey](https://github.com/ethanplusai/harvey), whose README describes a periodic decision loop and whose source is MIT-licensed. This implementation uses independently written code and does not incorporate or install that project. Harvey itself may rely on an existing model subscription and additional service costs; an MIT license alone is not evidence of a free, continuously running deployment.

Next production gates remain: protected Owner enrollment and agent-bound AI Passport, authenticated and revocable Guardian/Approval Gateway permits, durable server-side work intake with replay protection, trustworthy stop control and audit, isolated model execution, and independent QA. Preserve the Architect → HANTER → multiple federated orchestrators → scoped NCA architecture and the Public/Private and CRYPTO IMPERIAL boundaries.
