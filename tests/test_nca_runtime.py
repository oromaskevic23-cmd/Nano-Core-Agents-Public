"""Adversarial tests, with injected fake inference: NOT evidence of real LLM."""
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import unittest
from unittest.mock import patch

from nca_factory.factory import Factory
from nca_runtime.browser_snapshot import BrowserEvidence
from nca_runtime.ollama_adapter import InferenceDenied, LocalOllamaAdapter, ModelResult, ENDPOINT
from nca_runtime.pilot import PilotDenied, run_pilot, score_response


HTML = '<!doctype html><html><body><h1>IMPERIAL QA Fixture</h1><p>Page demo. A button has no descriptive label.</p></body></html>'
BLUEPRINT = {
    "tenant": "demo-tenant", "role": "website_qa", "domain": "software",
    "model": "smollm2:1.7b-instruct-q4_K_M", "skill": "legion:website-qa:demo",
    "orchestrator": "software-demo-orchestrator"
}


def sha(value):
    return hashlib.sha256(value.encode("utf8")).hexdigest()


def browser(_html):
    return BrowserEvidence(
        "IMPERIAL QA Fixture", "IMPERIAL QA Fixture Page demo. A button has no descriptive label.",
        sha(HTML), sha("synthetic-png-hash"), "MOCK_BROWSER_ONLY", True
    )


def response(_system, _task):
    text = json.dumps({
        "heading": "IMPERIAL QA Fixture",
        "finding": "The sample button lacks an accessible name.",
        "recommendation": "Add a descriptive visible label and verify keyboard behavior."
    })
    # INJECTED TEST FIXTURE. Must never be reported as genuine inference.
    return ModelResult(text, "ollama_local", BLUEPRINT["model"], sha(text), sha("mock-request"), True)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.factory = Factory(Path(temp.name) / "demo.sqlite")
        self.factory.register("nca-local-1", dict(BLUEPRINT), now=100)
        self.factory.start_exam("nca-local-1", now=101)
        for n in range(5):
            self.factory.record_mock_exam("nca-local-1", f"mock-case-{n}", "fixture-reviewer",
                                          95, False, sha(f"mock-{n}"), now=102+n)
        self.factory.mark_candidate("nca-local-1", now=110)

    def run_case(self, *, model=response, probe=browser, clock=lambda: 201, mission="mission-1"):
        return run_pilot(factory=self.factory, agent_id="nca-local-1",
                         blueprint=dict(BLUEPRINT), mission_id=mission,
                         action_id="action-1", html=HTML,
                         browser_probe=probe, model_call=model, clock=clock)

    def test_verified_mock_cycle_remains_unqualified(self):
        self.factory.open_mock_lease("nca-local-1", "mission-1", 100, 1, now=200)
        report = self.run_case()
        self.assertTrue(report["qa"]["passed"])
        self.assertFalse(report["professional_qualified"])
        self.assertFalse(report["production_authorized"])
        self.assertFalse(report["signed_ai_passport_verified"])
        self.assertEqual(report["real_world_actions"], 0)
        self.assertTrue(self.factory.audit_valid())

    def test_requires_active_lease(self):
        with self.assertRaisesRegex(PilotDenied, "AGENT_NOT_IN_LOCAL_MOCK_MISSION"):
            self.run_case()

    def test_mission_scoping(self):
        self.factory.open_mock_lease("nca-local-1", "mission-1", 50, 1, now=200)
        with self.assertRaisesRegex(PilotDenied, "MISSION_BINDING_MISMATCH"):
            self.run_case(mission="mission-2")

    def test_replay_is_denied(self):
        self.factory.open_mock_lease("nca-local-1", "mission-1", 100, 2, now=200)
        self.run_case()
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ACTION"):
            self.run_case()

    def test_stop_during_inference_invalidates_output(self):
        self.factory.open_mock_lease("nca-local-1", "mission-1", 100, 2, now=200)
        def stop_model(system, task):
            self.factory.stop_agent("nca-local-1", "emergency local stop", now=202)
            return response(system, task)
        with self.assertRaisesRegex(PilotDenied, "MISSION_STOPPED_EXPIRED_OR_REPROGRAMMED"):
            self.run_case(model=stop_model)

    def test_reprogram_during_inference_invalidates_output(self):
        self.factory.open_mock_lease("nca-local-1", "mission-1", 100, 2, now=200)
        def reprogram(system, task):
            updated = dict(BLUEPRINT, role="new-role")
            self.factory.reprogram("nca-local-1", updated, now=202)
            return response(system, task)
        with self.assertRaisesRegex(PilotDenied, "MISSION_STOPPED_EXPIRED_OR_REPROGRAMMED"):
            self.run_case(model=reprogram)

    def test_expiry_during_model_call(self):
        self.factory.open_mock_lease("nca-local-1", "mission-1", 3, 1, now=200)
        timestamps = iter((201, 201, 203, 203, 203))
        with self.assertRaisesRegex(PilotDenied, "MISSION_STOPPED_EXPIRED_OR_REPROGRAMMED"):
            self.run_case(clock=lambda: next(timestamps))

    def test_broken_browser_hash_fails_closed(self):
        self.factory.open_mock_lease("nca-local-1", "mission-1", 100, 1, now=200)
        def bad(html):
            valid = browser(html)
            return BrowserEvidence(valid.heading, valid.page_text, sha("wrong"),
                                   valid.screenshot_sha256, valid.network_block_rule, True)
        with self.assertRaisesRegex(PilotDenied, "BROWSER_DOCUMENT_MISMATCH"):
            self.run_case(probe=bad)

    def test_nonbrowser_stub_rejected(self):
        self.factory.open_mock_lease("nca-local-1", "mission-1", 100, 1, now=200)
        def bad(html):
            valid = browser(html)
            return BrowserEvidence(valid.heading, valid.page_text, valid.html_sha256,
                                   valid.screenshot_sha256, "NONE", False)
        with self.assertRaisesRegex(PilotDenied, "UNVERIFIED_BROWSER_SNAPSHOT"):
            self.run_case(probe=bad)

    def test_bad_grounding_and_hallucinated_actions_rejected(self):
        base = response("s", "t")
        altered = json.dumps({"heading": "FAKE", "finding": "I logged in to the bank account.",
                              "recommendation": "The job was published to https://example.org"})
        wrong = ModelResult(altered, base.provider, base.model_name, sha(altered),
                            base.model_request_sha256, True)
        verdict = score_response(wrong, browser(HTML))
        self.assertFalse(verdict.passed)
        self.assertIn("HEADING_NOT_GROUNDED", verdict.reason_codes)
        self.assertIn("PROHIBITED_CLAIM", verdict.reason_codes)

    def test_invalid_json_and_fake_model_call_are_rejected(self):
        bad = ModelResult("not JSON", "injected", "mock", sha("x"), sha("r"), False)
        verdict = score_response(bad, browser(HTML))
        self.assertFalse(verdict.passed)
        self.assertIn("NO_VERIFIED_LOCAL_MODEL_CALL", verdict.reason_codes)

    def test_adapter_denies_bad_model_timeout(self):
        for name in ("", "../secret", "invalid model", "x"*101):
            with self.assertRaises(InferenceDenied):
                LocalOllamaAdapter(name)
        with self.assertRaisesRegex(InferenceDenied, "INVALID_TIMEOUT"):
            LocalOllamaAdapter("safe-model", timeout_seconds=0)

    def test_adapter_request_is_only_localhost_and_no_tools(self):
        request_record = []
        class FakeResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self, n):
                return json.dumps({"model":"demo-model", "done":True,
                                   "message":{"role":"assistant", "content":'{"heading":"test"}'}}).encode()
        def stub(req, timeout):
            request_record.append(req)
            return FakeResponse()
        with patch("nca_runtime.ollama_adapter.urlopen", side_effect=stub):
            result = LocalOllamaAdapter("demo-model").generate("system", "task")
        self.assertTrue(result.actual_inference)  # simulated HTTP in mocked test!
        self.assertEqual(request_record[0].full_url, ENDPOINT)
        body = json.loads(request_record[0].data)
        self.assertFalse(body["stream"])
        self.assertNotIn("tools", body)
        self.assertEqual(body["keep_alive"], 0)

    def test_adapter_rejects_response_with_tool_calls(self):
        class FakeResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self, n):
                return json.dumps({"model":"demo-model", "done":True,
                                   "message":{"role":"assistant", "content":"{}", "tool_calls":[{}]}}).encode()
        with patch("nca_runtime.ollama_adapter.urlopen", return_value=FakeResponse()):
            with self.assertRaisesRegex(InferenceDenied, "UNSAFE_OR_EMPTY_MODEL_OUTPUT"):
                LocalOllamaAdapter("demo-model").generate("system", "task")


if __name__ == "__main__":
    unittest.main()
