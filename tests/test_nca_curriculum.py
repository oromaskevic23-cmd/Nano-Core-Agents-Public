"""Tests for synthetic NCA training-curriculum scheduling (no model training)."""
import unittest

from nca_factory.arena import generate_cases, reference_policy
from nca_factory.curriculum import plan_practice


def unsafe(_obs):
    return {"action": "USE", "tool": "primary"}


def passive(_obs):
    return {"action": "HOLD"}


class PracticeCurriculumTests(unittest.TestCase):
    def test_reference_policy_has_no_false_remediation(self):
        report = plan_practice(reference_policy, seed=11, cases=72)
        self.assertEqual(report["lesson_count"], 0)
        self.assertEqual(report["next_exercise_count"], 0)
        self.assertEqual(report["performance_diagnostic"]["critical_cases"], 0)
        self.assertEqual(report["performance_diagnostic"]["baseline_recoverable_missed"], 0)

    def test_unsafe_candidate_gets_safety_first(self):
        result = plan_practice(unsafe, seed=11, cases=72, max_exercises=24)
        self.assertGreater(result["performance_diagnostic"]["critical_cases"], 0)
        self.assertGreater(result["lesson_count"], 0)
        self.assertEqual(result["lessons"][0]["gap"], "CRITICAL_SAFETY")
        self.assertFalse(result["model_weights_updated"])
        self.assertFalse(result["production_authorized"])

    def test_passive_candidate_needs_productivity_practice(self):
        report = plan_practice(passive, seed=32, cases=72)
        self.assertEqual(report["performance_diagnostic"]["completed"], 0)
        self.assertGreater(report["performance_diagnostic"]["baseline_recoverable_missed"], 0)
        self.assertTrue(any(lesson["gap"] == "MISSED_VALID_WORK"
                            for lesson in report["lessons"]))

    def test_followup_cases_disjoint_and_derived_from_practice_only(self):
        seed = 33
        report = plan_practice(unsafe, seed=seed, cases=90)
        before = {case["case_id"] for case in generate_cases("practice", seed, 90)}
        after = {case["case_id"] for case in generate_cases("practice", report["next_seed"], 90)}
        protected = {case["case_id"] for case in generate_cases("holdout", seed, 90)}
        chosen = {case_id for lesson in report["lessons"]
                  for case_id in lesson["next_exercise_ids"]}
        self.assertEqual(report["initial_split"], "practice")
        self.assertEqual(report["next_split"], "practice")
        self.assertTrue(chosen.issubset(after))
        self.assertTrue(chosen.isdisjoint(before))
        self.assertTrue(chosen.isdisjoint(protected))
        self.assertEqual(len(chosen), report["next_exercise_count"])

    def test_same_policy_seed_and_budget_yield_same_plan(self):
        a = plan_practice(unsafe, seed=42, cases=72, max_exercises=12)
        b = plan_practice(unsafe, seed=42, cases=72, max_exercises=12)
        self.assertEqual(a, b)
        self.assertLessEqual(a["next_exercise_count"], 12)
        self.assertEqual(len(a["practice_manifest_sha256"]), 64)

    def test_no_production_data_or_training_claim(self):
        report = plan_practice(passive, cases=72)
        self.assertEqual(report["agents_trained"], 0)
        self.assertEqual(report["real_tool_calls"], 0)
        self.assertFalse(report["model_weights_updated"])
        self.assertFalse(report["test_answers_exposed"])
        self.assertFalse(report["professional_certified"])
        self.assertFalse(report["production_authorized"])

    def test_strict_exercise_limits(self):
        for x in (0, -1, 129, True, "12"):
            with self.assertRaises(ValueError):
                plan_practice(unsafe, seed=42, cases=72, max_exercises=x)


if __name__ == "__main__":
    unittest.main()
