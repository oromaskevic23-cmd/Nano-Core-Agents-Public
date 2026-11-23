"""Regression tests for the offline Universal NCA Factory simulation arena."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nca_factory.arena import (
    DOMAINS, evaluate_policy, evaluate_registered,
    generate_cases, reference_policy, run_episode,
)
from nca_factory.factory import Factory


def blueprint():
    return {
        "tenant": "imperial-lab",
        "role": "universal_nca",
        "domain": "software",
        "model": "MODEL-PLACEHOLDER-NO-INFERENCE",
        "skill": "LEGION:universal:synthetic",
        "orchestrator": "federated-domain-software",
    }


def always_execute(_observation):
    return {"action": "USE", "tool": "primary"}


def always_hold(_observation):
    return {"action": "HOLD"}


class UniversalArenaTests(unittest.TestCase):
    def test_seeded_cases_repeat_and_splits_are_disjoint(self):
        a = generate_cases("practice", 123, 54)
        self.assertEqual(a, generate_cases("practice", 123, 54))
        b = generate_cases("validation", 123, 54)
        c = generate_cases("holdout", 123, 54)
        self.assertEqual(len(set(t["case_id"] for t in a + b + c)), 162)
        self.assertNotEqual(a, generate_cases("practice", 124, 54))
        self.assertEqual(len(set(t["domain"] for t in a)), len(DOMAINS))

    def test_reference_baseline_is_reproducible(self):
        first = evaluate_policy(reference_policy, split="holdout", seed=7, cases=72)
        self.assertEqual(first, evaluate_policy(reference_policy, split="holdout", seed=7, cases=72))
        self.assertEqual(first["candidate_completions"], first["reference_baseline_completions"])
        self.assertEqual(first["safety_critical_cases"], 0)
        self.assertEqual(first["baseline_recoverable_missed"], 0)
        self.assertTrue(first["eligible_for_mock_review"])
        self.assertGreater(first["faults_recovered"], 0)
        self.assertEqual(first["actual_agents_trained"], 0)
        self.assertEqual(first["real_tool_calls"], 0)
        self.assertFalse(first["production_authorized"])

    def test_deterministic_mock_tool_failure_and_recovery(self):
        failed_primary = generate_cases("practice", 42, 18)[8]
        result = run_episode(failed_primary, reference_policy)
        self.assertTrue(result["completed"])
        self.assertTrue(result["fault_recovered"])
        self.assertEqual(result["attempts"], 2)
        self.assertFalse(result["critical"])

    def test_double_tool_failure_holds_without_fake_pass(self):
        task = generate_cases("practice", 42, 18)[9]
        result = run_episode(task, reference_policy)
        self.assertFalse(result["completed"])
        self.assertTrue(result["safe_hold"])
        self.assertEqual(result["attempts"], 2)
        self.assertFalse(result["critical"])

    def test_stop_and_tenant_boundary_always_deny(self):
        for index in (2, 3, 5, 12, 13, 14):
            task = generate_cases("practice", 42, 18)[index]
            result = run_episode(task, reference_policy)
            self.assertTrue(result["safe_hold"], index)
            self.assertEqual(result["mock_cost"], 0)
        for index in (2, 3):
            task = generate_cases("practice", 42, 18)[index]
            result = run_episode(task, always_execute)
            self.assertTrue(result["critical"])
            self.assertEqual(result["mock_cost"], 0)
            self.assertFalse(result["completed"])

    def test_prompt_injection_cannot_become_authority(self):
        task = generate_cases("practice", 7, 18)[11]
        self.assertIn("SYSTEM OVERRIDE", task["untrusted_note"])
        result = run_episode(task, reference_policy)
        self.assertTrue(result["completed"])
        self.assertFalse(result["critical"])
        denied = dict(task)
        denied["owner_stop"] = True
        self.assertTrue(run_episode(denied, reference_policy)["safe_hold"])

    def test_hidden_outcomes_and_case_id_not_in_policy_observation(self):
        observations = []
        def recorder(observation):
            observations.append(observation)
            return reference_policy(observation)
        run_episode(generate_cases("holdout", 42, 18)[8], recorder)
        self.assertGreaterEqual(len(observations), 3)
        for obs in observations:
            self.assertNotIn("tool_outcomes", obs)
            self.assertNotIn("case_id", obs)
            self.assertNotIn("expected_result", obs)

    def test_malicious_policy_fails_and_cannot_gain_real_authority(self):
        score = evaluate_policy(always_execute, split="validation", seed=42, cases=72)
        self.assertGreater(score["safety_critical_cases"], 0)
        self.assertFalse(score["eligible_for_mock_review"])
        self.assertFalse(score["production_authorized"])
        self.assertEqual(score["real_tool_calls"], 0)

    def test_lazy_policy_misses_reachable_work(self):
        score = evaluate_policy(always_hold, split="validation", seed=42, cases=72)
        self.assertEqual(score["candidate_completions"], 0)
        self.assertGreater(score["baseline_recoverable_missed"], 0)
        self.assertFalse(score["eligible_for_mock_review"])
        self.assertIsNone(score["mock_cost_per_completed"])

    def test_forged_receipt_is_critical(self):
        task = generate_cases("practice", 42, 3)[0]
        result = run_episode(task, lambda _o: {"action": "SUBMIT", "receipt": "f" * 64})
        self.assertTrue(result["critical"])
        self.assertFalse(result["completed"])

    def test_exceptions_and_unknown_commands_fail_closed(self):
        task = generate_cases("practice", 42, 3)[0]
        def broken(_o):
            raise RuntimeError("synthetic agent failed")
        for policy in (broken, lambda _o: {"action": "FREE_MONEY"}):
            report = run_episode(task, policy)
            self.assertTrue(report["critical"])
            self.assertEqual(report["mock_cost"], 0)

    def test_valid_lease_cost_bounds_and_role_scope(self):
        score = evaluate_policy(reference_policy, split="practice", seed=123, cases=72)
        self.assertGreater(score["mock_cost_units"], 0)
        self.assertGreater(score["mock_cost_per_completed"], 0)
        self.assertEqual(score["domains"].keys(), set(DOMAINS))
        self.assertEqual(sum(x["cases"] for x in score["domains"].values()), 72)
        self.assertNotEqual(score["trajectory_manifest_sha256"], "0" * 64)

    def test_registered_blueprint_is_bound_not_certified(self):
        with TemporaryDirectory() as folder:
            factory = Factory(Path(folder) / "agents.db")
            factory.register("NCA-ARENA-001", blueprint(), now=100)
            report = evaluate_registered(
                factory, "NCA-ARENA-001", reference_policy,
                split="holdout", seed=123, cases=36, now=101
            )
            identity = factory.inspect("NCA-ARENA-001", now=102)
            self.assertEqual(report["blueprint_sha256"], identity["blueprint_sha256"])
            self.assertEqual(report["version"], identity["version"])
            self.assertFalse(report["professional_certified"])
            self.assertEqual(identity["state"], "DRAFT")
            factory.stop_agent("NCA-ARENA-001", "test stop", now=103)
            with self.assertRaisesRegex(ValueError, "STOPPED_AGENT"):
                evaluate_registered(
                    factory, "NCA-ARENA-001", reference_policy,
                    split="holdout", seed=123, cases=36, now=104
                )

    def test_strict_arguments_and_scoped_evidence(self):
        for split, seed, count in (
            ("unknown", 1, 48), ("validation", True, 48),
            ("holdout", -1, 48), ("holdout", 7, 0),
            ("holdout", 7, 257), ("holdout", 7, True)
        ):
            with self.assertRaises(ValueError):
                generate_cases(split, seed, count)
        with self.assertRaises(ValueError):
            evaluate_policy(reference_policy, agent_id="", cases=36)
        with self.assertRaises(ValueError):
            evaluate_policy(reference_policy, blueprint_sha256="not-a-sha", cases=36)
        with self.assertRaises(ValueError):
            evaluate_policy(reference_policy, version=True, cases=36)

    def test_no_credential_or_llm_side_effects(self):
        report = evaluate_policy(reference_policy, split="practice", seed=1, cases=36)
        self.assertNotIn("passport_token", report)
        self.assertNotIn("approval_signature", report)
        self.assertNotIn("production_key", report)
        self.assertFalse(report["production_authorized"])
        self.assertEqual(report["real_reputation"], "UNRATED")
        self.assertEqual(report["actual_agents_trained"], 0)


if __name__ == "__main__":
    unittest.main()
