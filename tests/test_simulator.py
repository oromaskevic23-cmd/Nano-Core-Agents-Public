import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "nca_lab" / "simulator.py"
spec = importlib.util.spec_from_file_location("nca_simulator", SCRIPT)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


def case(action="DISPATCH"):
    return {"action": action, "classification": "PUBLIC", "passport": True,
            "skill": True, "guardian": True, "domain": True, "approval": True,
            "kill": False, "external_receipt": True}


class GateTests(unittest.TestCase):
    def test_all_combinations_match_reference_rules(self):
        self.assertEqual(lab.exhaustive_check(), 1536)

    def test_no_identity_skill_guardian_or_domain_fails_closed(self):
        for flag in ("passport", "skill", "guardian", "domain"):
            sample = case()
            sample[flag] = False
            self.assertEqual(lab.evaluate(sample)["decision"], "SIMULATED_HOLD")

    def test_kill_switch_blocks_even_if_other_fields_are_true(self):
        sample = case()
        sample["kill"] = True
        self.assertIn("KILL_SWITCH", lab.evaluate(sample)["reasons"])

    def test_external_effect_requires_approval_in_the_exercise(self):
        for action in ("DISPATCH", "PUBLISH", "PAYMENT_CONFIRM"):
            sample = case(action)
            sample["approval"] = False
            self.assertIn("MISSING_APPROVAL", lab.evaluate(sample)["reasons"])

    def test_private_or_secret_publication_is_held(self):
        for classification in ("PRIVATE", "SECRET"):
            sample = case("PUBLISH")
            sample["classification"] = classification
            self.assertIn("CLASSIFICATION_BOUNDARY", lab.evaluate(sample)["reasons"])

    def test_payment_assertion_without_external_receipt_is_held(self):
        sample = case("PAYMENT_CONFIRM")
        sample["external_receipt"] = False
        self.assertIn("MISSING_EXTERNAL_RECEIPT", lab.evaluate(sample)["reasons"])

    def test_reject_missing_unknown_and_untyped_fields(self):
        for sample in (case() | {"approval": "true"}, case() | {"extra": 1},
                       {k: v for k, v in case().items() if k != "guardian"}):
            with self.assertRaises(ValueError):
                lab.evaluate(sample)

    def test_repeatability_and_no_real_effects(self):
        first = lab.run(1000, 42)
        self.assertEqual(first, lab.run(1000, 42))
        self.assertNotEqual(first["case_stream_sha256"], lab.run(1000, 43)["case_stream_sha256"])
        self.assertEqual(first["oracle_mismatches"], 0)
        self.assertEqual((first["agents_trained"], first["real_executions"], first["external_effects"]), (0, 0, 0))

    def test_decision_never_grants_real_authority(self):
        result = lab.evaluate(case())
        self.assertEqual(result["decision"], "SIMULATED_ALLOW")
        self.assertFalse(result["real_execution_allowed"])

    def test_resource_bounds(self):
        for amount in (0, -1, 1_000_001, True):
            with self.assertRaises(ValueError):
                lab.run(amount, 1)


if __name__ == "__main__":
    unittest.main()
