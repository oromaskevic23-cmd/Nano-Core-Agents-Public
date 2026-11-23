"""Signed queue -> local browser/model worker boundary tests (model is injected)."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from nca_control.queue import LocalQueue
from nca_control.protocol import encode, Rejected
from nca_control.worker import run_one
from nca_runtime.browser_snapshot import BrowserEvidence
from nca_runtime.ollama_adapter import ModelResult


HTML = "<!doctype html><html lang='en'><body><h1>IMPERIAL Offline Audit</h1><p>Demo button has no visible label.</p></body></html>"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def browser(html):
    return BrowserEvidence("IMPERIAL Offline Audit",
        "IMPERIAL Offline Audit Demo button has no visible label.",
        sha(html),sha("PNG"),"ALL_REQUESTS_ABORTED_IN_BROWSER_CONTEXT",True)


def model(system,question):
    output=json.dumps({"heading":"IMPERIAL Offline Audit",
                       "finding":"This example button lacks a descriptive label.",
                       "recommendation":"Add a visible descriptive text label to the button."})
    return ModelResult(output,"ollama_local","injected-model-fixture",
                       sha(output),sha("test-request"),True)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        directory=TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.queue=LocalQueue(Path(directory.name)/"state.sqlite")
        key=Ed25519PrivateKey.generate()
        pub=key.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        p={"version":1,"issuer":"HANTER-LAB-ONLY",
           "audience":"LOCAL_SYNTHETIC_ONLY","agent_id":"nca-001",
           "job_id":"one-job","tenant_id":"test-tenant",
           "document_sha256":sha(HTML),"blueprint_sha256":sha("demo-blueprint-v1"),
           "nonce":"b"*32,"issued_at":100,"expires_at":300}
        env={"payload":p,"key_id":"DEMO-worker",
             "signature":key.sign(encode(p,"DEMO-worker")).hex()}
        self.queue.submit(env,{"DEMO-worker":pub},now=110)

    def run_case(self,**changes):
        data={"html":HTML,"worker_id":"worker1","browser_probe":browser,
              "model_call":model,"clock":lambda:111}
        data.update(changes)
        return run_one(self.queue,**data)

    def test_end_to_end_signed_queue_and_qa(self):
        result=self.run_case()
        self.assertEqual(result["state"],"LOCAL_QA_PASS")
        self.assertFalse(result["production_authorized"])
        self.assertFalse(result["signed_ai_passport_verified"])
        self.assertTrue(self.queue.audit_valid())

    def test_wrong_document_cannot_execute(self):
        with self.assertRaisesRegex(Rejected,"PERMIT_DOCUMENT_MISMATCH"):
            self.run_case(html=HTML+"<p>modified</p>")

    def test_stop_during_model_prevents_finish(self):
        def stop_during(_system,_task):
            self.queue.stop("agent","nca-001","manual stop",now=112)
            return model(_system,_task)
        with self.assertRaises(Rejected):
            self.run_case(model_call=stop_during)
        self.assertEqual(self.queue.inspect("one-job")["state"],"STOPPED")

    def test_delayed_response_after_expiry_is_blocked(self):
        sequence=iter([111,111,111,300])
        with self.assertRaisesRegex(Rejected,"STOPPED_OR_EXPIRED"):
            self.run_case(clock=lambda:next(sequence))

    def test_failed_quality_is_not_promoted(self):
        def weak(_system,_task):
            raw='{"heading":"wrong","finding":"too short","recommendation":"none"}'
            return ModelResult(raw,"ollama_local","mock",sha(raw),sha("r"),True)
        result=self.run_case(model_call=weak)
        self.assertEqual(result["state"],"LOCAL_QA_FAIL")
        self.assertIn("HEADING_NOT_GROUNDED",result["qa_reasons"])

    def test_unverified_browser_rejected(self):
        def spoof(html):
            good=browser(html)
            return BrowserEvidence(good.heading,good.page_text,good.html_sha256,
                                   good.screenshot_sha256,good.network_block_rule,False)
        with self.assertRaisesRegex(Rejected,"UNTRUSTED_BROWSER_EVIDENCE"):
            self.run_case(browser_probe=spoof)

    def test_stop_after_browser_prevents_model_call(self):
        calls=[]
        def browser_then_stop(html):
            result=browser(html)
            self.queue.stop("agent","nca-001","local stop",now=112)
            return result
        def forbidden_model(_system,_question):
            calls.append(True)
            return model(_system,_question)
        with self.assertRaises(Rejected):
            self.run_case(browser_probe=browser_then_stop,model_call=forbidden_model)
        self.assertEqual(calls,[])

    def test_wrong_blueprint_cannot_execute_browser(self):
        import sqlite3
        with sqlite3.connect(self.queue.path) as db:
            db.execute("UPDATE jobs SET blueprint=? WHERE job_id='one-job'",(sha("other"),))
        calls=[]
        with self.assertRaisesRegex(Rejected,"PERMIT_BLUEPRINT_MISMATCH"):
            self.run_case(browser_probe=lambda html:calls.append(html))
        self.assertEqual(calls,[])


if __name__=="__main__":
    unittest.main()
