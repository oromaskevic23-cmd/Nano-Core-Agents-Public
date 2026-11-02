"""Explicitly opted-in single local model/browser pilot; no production grant."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from nca_factory.factory import Factory
from .browser_snapshot import snapshot_owned_html
from .ollama_adapter import LocalOllamaAdapter
from .pilot import run_pilot


OWNED_HTML = """<!doctype html><html lang="en"><meta charset="utf-8">
<title>IMPERIAL NCA synthetic audit</title><body>
<h1>IMPERIAL Synthetic Website QA</h1>
<p>A demo action button is missing an accessible text label.</p>
<button aria-label="">✓</button></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Free one-agent LOCAL browser+Ollama pilot; no external sites")
    parser.add_argument("--live", action="store_true",
                        help="Use existing local Ollama and Chromium: one real inference")
    parser.add_argument("--model", default="smollm2:1.7b-instruct-q4_K_M")
    args = parser.parse_args()
    if not args.live:
        parser.error("Nothing is faked as real inference. Explicit --live required.")
    if os.environ.get("IMPERIAL_NCA_LOCAL_LLM") != "ALLOW_LOCAL_SYNTHETIC_INFERENCE":
        parser.error("Set IMPERIAL_NCA_LOCAL_LLM=ALLOW_LOCAL_SYNTHETIC_INFERENCE")
    blueprint = {
        "tenant": "synthetic-local", "role": "website_qa",
        "domain": "software", "model": args.model,
        "skill": "LEGION:website-qa:synthetic",
        "orchestrator": "federated-software-demo"
    }
    # The five local scores are DEMONSTRATION FIXTURES, NOT examinations.
    # They are only needed to exercise the existing offline Factory API.
    with tempfile.TemporaryDirectory(prefix="imperial-nca-pilot-") as tmp:
        factory = Factory(Path(tmp) / "pilot.sqlite")
        factory.register("NCA-LOCAL-001", blueprint)
        factory.start_exam("NCA-LOCAL-001")
        for index in range(5):
            factory.record_mock_exam(
                "NCA-LOCAL-001", "local-fixture-" + str(index + 1),
                "untrusted-demo-rubric", 95, False,
                hashlib.sha256(f"synthetic-rubric-{index}".encode()).hexdigest())
        factory.mark_candidate("NCA-LOCAL-001")
        factory.open_mock_lease("NCA-LOCAL-001", "local-website-qa", 90, 1)
        report = run_pilot(
            factory=factory,
            agent_id="NCA-LOCAL-001", blueprint=blueprint,
            mission_id="local-website-qa", action_id="single-local-step",
            html=OWNED_HTML,
            browser_probe=snapshot_owned_html,
            model_call=LocalOllamaAdapter(args.model, timeout_seconds=45).generate
        )
        report["local_mock_fixtures_used"] = 5
        report["authorship"] = "Alexander Nikolaevich Romaskevich (RomaskevicH)"
        report["local_audit_hash_chain_valid"] = factory.audit_valid()
        report["real_owner_identity_proven"] = False
        report["real_customer_task_completed"] = False
        # No untrusted model raw output or API secrets in CI logs.
        print(json.dumps(report, sort_keys=True, indent=2))
        if not report["qa"]["passed"]:
            raise SystemExit("QA_FAILED_RETAIN_EVIDENCE_NO_COMMERCIAL_ACCESS")


if __name__ == "__main__":
    main()
