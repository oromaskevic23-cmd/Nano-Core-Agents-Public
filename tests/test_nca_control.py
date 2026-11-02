"""Real Ed25519, persistent local queue, no production rights."""
import hashlib
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from nca_control.protocol import Rejected, encode, validate
from nca_control.queue import LocalQueue


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class LocalControlTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)/"queue.sqlite"
        self.store = LocalQueue(self.path)
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.trust={"DEMO-test":public}

    def signed(self, **updates):
        p = {
            "version":1,"issuer":"HANTER-LAB-ONLY",
            "audience":"LOCAL_SYNTHETIC_ONLY",
            "agent_id":"NCA-test","job_id":"job-001","tenant_id":"lab",
            "document_sha256":digest("fixture"),
            "blueprint_sha256":digest("blueprint"),
            "nonce":"a"*32,"issued_at":100,"expires_at":300}
        p.update(updates)
        kid="DEMO-test"
        return {"payload":p,"key_id":kid,
                "signature":self.private.sign(encode(p,kid)).hex()}

    def test_real_signature_validates_and_scope_is_local(self):
        result=validate(self.signed(),self.trust,now=110)
        self.assertEqual(result["audience"],"LOCAL_SYNTHETIC_ONLY")

    def test_bad_signature_fails(self):
        env=self.signed()
        env["signature"]="0"*128
        with self.assertRaisesRegex(Rejected,"BAD_SIGNATURE"):
            validate(env,self.trust,now=110)

    def test_tampering_signed_document_fails(self):
        env=self.signed()
        env["payload"]["document_sha256"]=digest("changed")
        with self.assertRaisesRegex(Rejected,"BAD_SIGNATURE"):
            validate(env,self.trust,now=110)

    def test_foreign_key_and_expired_permit(self):
        env=self.signed()
        with self.assertRaisesRegex(Rejected,"UNKNOWN_DEMO_KEY"):
            validate(env,{},now=110)
        with self.assertRaisesRegex(Rejected,"EXPIRED"):
            validate(env,self.trust,now=300)

    def test_permit_cannot_raise_audience_or_ttl(self):
        with self.assertRaisesRegex(Rejected,"BAD_SCOPE"):
            validate(self.signed(audience="PRODUCTION"),self.trust,now=110)
        with self.assertRaisesRegex(Rejected,"EXPIRED"):
            validate(self.signed(expires_at=401),self.trust,now=110)

    def test_submit_claim_complete_survive_restart(self):
        self.store.submit(self.signed(),self.trust,now=110)
        reopened=LocalQueue(self.path)
        claim=reopened.claim("worker-A",now=111)
        self.assertEqual(claim["document_sha256"],digest("fixture"))
        self.assertEqual(claim["agent_id"],"NCA-test")
        result=reopened.finish("job-001","worker-A",claim["claim_token"],
                               digest("qa-evidence"),True,now=112)
        self.assertEqual(result["state"],"LOCAL_QA_PASS")
        self.assertFalse(result["production_authorized"])
        self.assertEqual(LocalQueue(self.path).inspect("job-001")["state"],"LOCAL_QA_PASS")
        self.assertTrue(reopened.audit_valid())

    def test_nonce_and_job_replay_after_restart(self):
        self.store.submit(self.signed(),self.trust,now=110)
        with self.assertRaisesRegex(Rejected,"REPLAY_OR_DUPLICATE"):
            LocalQueue(self.path).submit(self.signed(),self.trust,now=110)
        with self.assertRaisesRegex(Rejected,"REPLAY_OR_DUPLICATE"):
            self.store.submit(self.signed(job_id="job-002"),self.trust,now=110)

    def test_one_worker_cannot_complete_another_claim(self):
        self.store.submit(self.signed(),self.trust,now=110)
        claim=self.store.claim("worker-A",now=111)
        with self.assertRaisesRegex(Rejected,"CLAIM_PROOF_REQUIRED"):
            self.store.finish("job-001","worker-B",claim["claim_token"],
                              digest("result"),True,now=112)
        with self.assertRaisesRegex(Rejected,"CLAIM_PROOF_REQUIRED"):
            self.store.finish("job-001","worker-A","fake",
                              digest("result"),True,now=112)

    def test_expiry_blocks_claim_and_completion(self):
        self.store.submit(self.signed(expires_at=112),self.trust,now=110)
        claim=self.store.claim("worker-A",now=111)
        with self.assertRaisesRegex(Rejected,"STOPPED_OR_EXPIRED"):
            self.store.finish("job-001","worker-A",claim["claim_token"],
                              digest("result"),True,now=112)

    def test_pending_mission_expired_no_claim(self):
        self.store.submit(self.signed(expires_at=112),self.trust,now=110)
        self.assertIsNone(self.store.claim("worker-A",now=112))
        self.assertEqual(self.store.inspect("job-001")["state"],"EXPIRED")

    def test_agent_stop_midflight_blocks_result(self):
        self.store.submit(self.signed(),self.trust,now=110)
        claim=self.store.claim("worker-A",now=111)
        self.store.stop("agent","NCA-test","manual emergency stop",now=112)
        self.assertEqual(self.store.inspect("job-001")["state"],"STOPPED")
        with self.assertRaises(Rejected):
            self.store.finish("job-001","worker-A",claim["claim_token"],
                              digest("result"),True,now=113)
        self.assertTrue(LocalQueue(self.path).audit_valid())

    def test_global_stop_prevents_new_signed_jobs(self):
        self.store.stop("global","*","local operator stop",now=105)
        with self.assertRaisesRegex(Rejected,"STOPPED"):
            LocalQueue(self.path).submit(self.signed(),self.trust,now=110)

    def test_no_double_completion(self):
        self.store.submit(self.signed(),self.trust,now=110)
        claim=self.store.claim("worker-A",now=111)
        self.store.finish("job-001","worker-A",claim["claim_token"],digest("r"),False,now=112)
        with self.assertRaisesRegex(Rejected,"JOB_NOT_CLAIMED"):
            self.store.finish("job-001","worker-A",claim["claim_token"],digest("r"),True,now=113)
        self.assertEqual(self.store.inspect("job-001")["state"],"LOCAL_QA_FAIL")

    def test_audit_detects_database_tamper(self):
        self.store.submit(self.signed(),self.trust,now=110)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE audit SET event='{}' WHERE seq=1")
        self.assertFalse(self.store.audit_valid())


if __name__=="__main__":
    unittest.main()
