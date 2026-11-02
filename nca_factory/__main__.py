"""Run an ephemeral local-only factory demonstration without credentials.

Usage: python3 -m nca_factory
All entities, reviews and missions are synthetic. No model inference or tools.
"""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .factory import Factory


def main():
    blueprint = {
        "tenant": "imperial-lab",
        "role": "universal_quality_research",
        "domain": "software",
        "model": "VELION-contract-placeholder",
        "skill": "LEGION:quality_research:design",
        "orchestrator": "demo-software-orchestrator"
    }
    with TemporaryDirectory(prefix="imperial-nca-factory-") as directory:
        engine = Factory(Path(directory) / "demo.db")
        engine.register("NCA-DEMO-001", blueprint, now=100)
        engine.start_exam("NCA-DEMO-001", now=101)
        for i in range(5):
            engine.record_mock_exam(
                "NCA-DEMO-001", f"demo-case-{i + 1}", "offline-rubric-fixture",
                95, False, hashlib.sha256(f"synthetic-{i}".encode()).hexdigest(),
                now=102+i
            )
        engine.mark_candidate("NCA-DEMO-001", now=110)
        engine.open_mock_lease("NCA-DEMO-001", "mission-001", 120, 2, now=110)
        engine.mock_step("NCA-DEMO-001", "step-1", hashlib.sha256(b"mock-input").hexdigest(), now=111)
        before_stop = engine.inspect("NCA-DEMO-001", now=111)
        engine.stop_agent("NCA-DEMO-001", "local stop demonstration", now=112)
        after_stop = engine.inspect("NCA-DEMO-001", now=112)
        revised = engine.reprogram("NCA-DEMO-001", dict(blueprint, role="universal_analyst"), now=113)
        print(json.dumps({
            "status": "OFFLINE_SIMULATION_ONLY",
            "candidate_before_stop": before_stop,
            "stopped": after_stop,
            "new_revision_after_reprogram": revised,
            "audit_chain_valid": engine.audit_valid(),
            "real_llm_calls": 0,
            "actual_workers": 0,
            "commercial_permissions": 0,
            "real_reputation": "UNRATED"
        }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
