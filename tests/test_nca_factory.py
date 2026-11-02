"""Offline-only acceptance and adversarial tests for the NCA Factory MVP."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nca_factory.factory import Denied, Factory


def spec(**changes):
    data = {
        "tenant": "imperial-lab",
        "role": "website_qa",
        "domain": "software",
        "model": "VELION-model-contract-only",
        "skill": "legion:website_qa:design",
        "orchestrator": "software-orchestrator-A"
    }
    data.update(changes)
    return data


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / "factory.db"
        self.factory = Factory(self.db)
        self.factory.register("nca-001", spec(), now=100)

    def advance(self, count=5, *, critical_case=None, score=95):
        self.factory.start_exam("nca-001", now=101)
        for i in range(count):
            self.factory.record_mock_exam(
                "nca-001", f"case-{i}", "mock-reviewer", score,
                critical_case == i, sha(f"evidence-{i}"), now=102 + i)

    def ready(self):
        self.advance()
        self.factory.mark_candidate("nca-001", now=110)

    def test_register_is_draft_and_noncommercial(self):
        s = self.factory.inspect("nca-001", now=100)
        self.assertEqual(s["version"], 1)
        self.assertEqual(s["state"], "DRAFT")
        self.assertFalse(s["production_permitted"])
        self.assertFalse(s["professional_certified"])
        self.assertEqual(s["external_reputation"], "UNRATED")

    def test_duplicate_agent_rejected(self):
        with self.assertRaisesRegex(Denied, "DUPLICATE_AGENT"):
            self.factory.register("nca-001", spec(), now=100)

    def test_missing_field_cannot_register(self):
        with self.assertRaisesRegex(Denied, "INVALID_BLUEPRINT_SCHEMA"):
            self.factory.register("nca-002", {"tenant": "x"}, now=100)

    def test_cannot_skip_exam(self):
        with self.assertRaisesRegex(Denied, "NOT_OFFLINE_CANDIDATE"):
            self.factory.open_mock_lease("nca-001", "mission", 20, 1, now=110)

    def test_mock_candidate_pass_does_not_certify(self):
        self.ready()
        s = self.factory.inspect("nca-001", now=110)
        self.assertEqual(s["state"], "OFFLINE_CANDIDATE")
        self.assertEqual(s["mock_case_count"], 5)
        self.assertEqual(s["mock_average_score"], 95)
        self.assertFalse(s["production_permitted"])
        self.assertEqual(s["external_reputation"], "UNRATED")

    def test_insufficient_cases_fail(self):
        self.advance(count=4)
        with self.assertRaisesRegex(Denied, "EXAM_GATE_FAILED"):
            self.factory.mark_candidate("nca-001", now=110)

    def test_low_score_fails(self):
        self.advance(score=79)
        with self.assertRaisesRegex(Denied, "EXAM_GATE_FAILED"):
            self.factory.mark_candidate("nca-001", now=110)

    def test_critical_defect_blocks_even_with_good_average(self):
        self.advance(critical_case=2)
        with self.assertRaisesRegex(Denied, "EXAM_GATE_FAILED"):
            self.factory.mark_candidate("nca-001", now=110)

    def test_duplicate_exam_and_self_review_denied(self):
        self.factory.start_exam("nca-001", now=101)
        with self.assertRaisesRegex(Denied, "SELF_REVIEW_FORBIDDEN"):
            self.factory.record_mock_exam("nca-001", "case-0", "nca-001", 100, False, sha("e"), now=101)
        self.factory.record_mock_exam("nca-001", "case-0", "reviewer", 100, False, sha("e"), now=101)
        with self.assertRaisesRegex(Denied, "DUPLICATE_EXAM_CASE"):
            self.factory.record_mock_exam("nca-001", "case-0", "reviewer", 100, False, sha("e"), now=101)

    def test_invalid_score_flags_and_digests_denied(self):
        self.factory.start_exam("nca-001", now=101)
        for value in (-1, 101, True):
            with self.assertRaises(Denied):
                self.factory.record_mock_exam("nca-001", "case-0", "reviewer", value, False, sha("e"), now=101)
        with self.assertRaisesRegex(Denied, "INVALID_SCORE"):
            self.factory.record_mock_exam("nca-001", "case-0", "reviewer", 95, 1, sha("e"), now=101)
        with self.assertRaisesRegex(Denied, "INVALID_EVIDENCE_DIGEST"):
            self.factory.record_mock_exam("nca-001", "case-0", "reviewer", 95, False, "fake", now=101)

    def test_finite_lease_and_expiry(self):
        self.ready()
        deadline = self.factory.open_mock_lease("nca-001", "mission-a", 10, 2, now=200)
        self.assertEqual(deadline, 210)
        step = self.factory.mock_step("nca-001", "action-1", sha("input"), now=209)
        self.assertFalse(step["real_execution"])
        with self.assertRaisesRegex(Denied, "MISSION_EXPIRED"):
            self.factory.mock_step("nca-001", "action-2", sha("input"), now=210)
        self.assertEqual(self.factory.inspect("nca-001", now=210)["state"], "MOCK_EXPIRED")

    def test_step_quota_and_replay_guard(self):
        self.ready()
        self.factory.open_mock_lease("nca-001", "mission-a", 60, 1, now=200)
        self.factory.mock_step("nca-001", "action-1", sha("payload"), now=201)
        with self.assertRaisesRegex(Denied, "TASK_QUOTA_EXCEEDED"):
            self.factory.mock_step("nca-001", "action-2", sha("payload"), now=202)
        self.assertTrue(self.factory.audit_valid())

    def test_replay_guard_with_more_quota(self):
        self.ready()
        self.factory.open_mock_lease("nca-001", "mission-a", 60, 2, now=200)
        self.factory.mock_step("nca-001", "action-1", sha("payload"), now=201)
        with self.assertRaisesRegex(Denied, "DUPLICATE_ACTION"):
            self.factory.mock_step("nca-001", "action-1", sha("different"), now=202)

    def test_stop_persists_across_reopen(self):
        self.ready()
        self.factory.open_mock_lease("nca-001", "mission-a", 60, 2, now=200)
        self.factory.stop_agent("nca-001", "Manual disable", now=202)
        reopened = Factory(self.db)
        self.assertEqual(reopened.inspect("nca-001", now=203)["state"], "STOPPED")
        with self.assertRaises(Denied):
            reopened.mock_step("nca-001", "action-1", sha("payload"), now=203)
        self.assertTrue(reopened.audit_valid())

    def test_reprogram_invalidates_qualification_and_lease(self):
        self.ready()
        self.factory.open_mock_lease("nca-001", "mission-a", 60, 2, now=200)
        old_hash = self.factory.inspect("nca-001", now=201)["blueprint_sha256"]
        updated = self.factory.reprogram("nca-001", spec(role="data_analyst"), now=202)
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["state"], "DRAFT")
        self.assertNotEqual(updated["blueprint_sha256"], old_hash)
        self.assertEqual(updated["mock_case_count"], 0)
        self.assertEqual(updated["prior_revision_case_count"], 5)
        self.assertIsNone(updated["mock_lease_deadline"])
        with self.assertRaisesRegex(Denied, "NOT_MOCK_ACTIVE"):
            self.factory.mock_step("nca-001", "action-2", sha("payload"), now=203)

    def test_reprogram_after_stop_requires_new_exam(self):
        self.factory.stop_agent("nca-001", "Manual change request", now=102)
        updated = self.factory.reprogram("nca-001", spec(role="support"), now=103)
        self.assertEqual(updated["version"], 2)
        self.assertEqual(updated["state"], "DRAFT")
        with self.assertRaises(Denied):
            self.factory.open_mock_lease("nca-001", "mission-b", 60, 1, now=104)

    def test_global_stop_persists_and_blocks_reprogram(self):
        self.factory.stop_all("Owner shutdown", now=105)
        reopened = Factory(self.db)
        with self.assertRaisesRegex(Denied, "GLOBAL_STOP"):
            reopened.register("nca-002", spec(), now=106)
        with self.assertRaisesRegex(Denied, "GLOBAL_STOP"):
            reopened.reprogram("nca-001", spec(role="other"), now=106)
        self.assertEqual(reopened.inspect("nca-001", now=106)["state"], "STOPPED")

    def test_negative_ttl_and_bool_flags_denied(self):
        self.ready()
        with self.assertRaisesRegex(Denied, "INVALID_MISSION_TTL"):
            self.factory.open_mock_lease("nca-001", "m", 0, 1, now=200)
        with self.assertRaisesRegex(Denied, "INVALID_STEP_QUOTA"):
            self.factory.open_mock_lease("nca-001", "m", 30, True, now=200)

    def test_audit_detects_simple_tamper(self):
        self.assertTrue(self.factory.audit_valid())
        with sqlite3.connect(self.db) as cx:
            cx.execute("UPDATE audit SET entry='{}' WHERE seq=1")
        self.assertFalse(self.factory.audit_valid())


if __name__ == "__main__":
    unittest.main()
