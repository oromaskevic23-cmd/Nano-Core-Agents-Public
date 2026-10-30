import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "nca_lab" / "handoff_guard.py"
spec = importlib.util.spec_from_file_location("nca_handoff_guard", MODULE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def registry():
    return {
        "NCA-1": {"organization_id": "IMPERIAL", "workspace_id": "engineering", "active": True,
                  "skills": ["RESEARCH"], "browser_namespace": "browser-1"},
        "NCA-2": {"organization_id": "IMPERIAL", "workspace_id": "engineering", "active": True,
                  "skills": ["RESEARCH", "CODE", "BROWSER_READ", "PUBLISH", "PAYMENT_CONFIRM"],
                  "browser_namespace": "browser-2"},
    }


def request(action="BROWSER_READ"):
    return {"task_id": "TASK-001", "sender_id": "NCA-1", "receiver_id": "NCA-2",
            "organization_id": "IMPERIAL", "workspace_id": "engineering", "action": action,
            "classification": "PUBLIC", "browser_namespace": "browser-2",
            "approval_ref": None, "external_receipt_ref": None,
            "estimated_cost_usd": 0, "kill_switch": False}


class HandoffGuardTests(unittest.TestCase):
    def test_allowed_same_org_research_or_browser_does_not_grant_authority(self):
        for action in ("RESEARCH", "BROWSER_READ", "CODE"):
            result = guard.evaluate_handoff(request(action), registry())
            self.assertEqual(result["decision"], "SIMULATED_ALLOW")
            self.assertFalse(result["real_execution_allowed"])
            self.assertFalse(result["real_approvals_verified"])
            self.assertEqual(result["external_effects"], 0)

    def test_cross_organization_denied(self):
        agents = registry()
        agents["NCA-2"]["organization_id"] = "OTHER"
        self.assertIn("RECEIVER_ORGANIZATION_BOUNDARY", guard.evaluate_handoff(request(), agents)["reasons"])

    def test_cross_workspace_denied(self):
        agents = registry()
        agents["NCA-2"]["workspace_id"] = "finance"
        self.assertIn("RECEIVER_WORKSPACE_BOUNDARY", guard.evaluate_handoff(request(), agents)["reasons"])

    def test_browser_namespace_spoof_denied(self):
        req = request()
        req["browser_namespace"] = "browser-1"
        self.assertIn("BROWSER_ISOLATION", guard.evaluate_handoff(req, registry())["reasons"])

    def test_browser_namespace_collisions_denied(self):
        agents = registry()
        agents["NCA-1"]["browser_namespace"] = "browser-2"
        self.assertIn("BROWSER_NAMESPACE_COLLISION", guard.evaluate_handoff(request(), agents)["reasons"])

    def test_kill_switch_and_free_only(self):
        req = request()
        req["kill_switch"] = True
        req["estimated_cost_usd"] = 0.01
        self.assertEqual(set(guard.evaluate_handoff(req, registry())["reasons"]), {"KILL_SWITCH", "FREE_ONLY_COST"})

    def test_revoked_unknown_skill_and_self_handoff(self):
        agents = registry()
        agents["NCA-2"]["active"] = False
        agents["NCA-2"]["skills"] = []
        req = request()
        req["sender_id"] = "NCA-2"
        self.assertTrue({"SELF_HANDOFF", "RECEIVER_INACTIVE", "RECEIVER_SKILL_MISSING"}.issubset(guard.evaluate_handoff(req, agents)["reasons"]))
        req["sender_id"] = "MISSING"
        self.assertIn("UNKNOWN_AGENT", guard.evaluate_handoff(req, agents)["reasons"])

    def test_secret_classification_fails_closed(self):
        req = request("CODE")
        req["classification"] = "SECRET"
        self.assertIn("SECRET_HANDOFF_DENIED", guard.evaluate_handoff(req, registry())["reasons"])

    def test_publication_requires_approval_and_public_scope(self):
        req = request("PUBLISH")
        req["classification"] = "PRIVATE"
        self.assertEqual(set(guard.evaluate_handoff(req, registry())["reasons"]), {"APPROVAL_REQUIRED", "PUBLIC_PRIVATE_BOUNDARY"})

    def test_payment_confirmation_needs_external_receipt(self):
        req = request("PAYMENT_CONFIRM")
        req["approval_ref"] = "SYNTHETIC-APPROVAL"
        self.assertIn("EXTERNAL_RECEIPT_REQUIRED", guard.evaluate_handoff(req, registry())["reasons"])
        req["external_receipt_ref"] = "SYNTHETIC-RECEIPT"
        result = guard.evaluate_handoff(req, registry())
        self.assertEqual(result["decision"], "SIMULATED_ALLOW")
        self.assertFalse(result["real_execution_allowed"])

    def test_schema_rejects_untrusted_extra_fields(self):
        cases = [request() | {"extra": "bad"}, request() | {"kill_switch": "false"},
                 request() | {"estimated_cost_usd": True}, request() | {"estimated_cost_usd": -1},
                 request() | {"action": []}, request() | {"classification": {}},
                 request() | {"estimated_cost_usd": float("nan")},
                 {k: v for k, v in request().items() if k != "task_id"}]
        for req in cases:
            with self.subTest(req=req):
                with self.assertRaises(ValueError):
                    guard.evaluate_handoff(req, registry())

    def test_audit_digest_repeatable_and_changes_on_input(self):
        first = guard.evaluate_handoff(request(), registry())
        self.assertEqual(first, guard.evaluate_handoff(request(), registry()))
        changed = request()
        changed["kill_switch"] = True
        self.assertNotEqual(first["audit_sha256"], guard.evaluate_handoff(changed, registry())["audit_sha256"])
        changed_registry = registry()
        changed_registry["NCA-2"]["skills"].remove("RESEARCH")
        self.assertNotEqual(first["audit_sha256"], guard.evaluate_handoff(request(), changed_registry)["audit_sha256"])


if __name__ == "__main__":
    unittest.main()
