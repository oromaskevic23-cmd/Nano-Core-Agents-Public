"""Real local process and queue recovery tests; no real model or customer work."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import time
from tempfile import TemporaryDirectory
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from nca_control.always_on import run_loop, supervise_claim
from nca_control.protocol import Rejected, encode
from nca_control.queue import LocalQueue


def _finish_synthetic(path, claim, worker, _model):
    # Test fixture only: no browser/model or professional QA is claimed.
    LocalQueue(path).finish(claim["job_id"],worker,claim["claim_token"],
                            hashlib.sha256(b"synthetic").hexdigest(),True,int(time.time()))


def _slow_synthetic(_path, _claim, _worker, marker):
    Path(marker).write_text("started",encoding="utf8")
    time.sleep(20)


def _crash_synthetic(_path, _claim, _worker, _model):
    os._exit(17)


def _slow_with_child(_path, _claim, _worker, folder):
    os.setsid()
    root=Path(folder)
    subprocess.Popen([sys.executable,"-c",
        "import pathlib,signal,sys,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        "pathlib.Path(sys.argv[1]).write_text('ready'); time.sleep(1.5); pathlib.Path(sys.argv[2]).write_text('still-running')",
        str(root/"descendant-ready"),str(root/"descendant-survived")])
    deadline=time.monotonic()+5
    while not (root/"descendant-ready").exists() and time.monotonic()<deadline:
        time.sleep(0.01)
    (root/"child-started").write_text("started",encoding="utf8")
    time.sleep(20)


class AlwaysOnTests(unittest.TestCase):
    def setUp(self):
        folder=TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root=Path(folder.name)
        self.queue=LocalQueue(self.root/"lab.sqlite")
        self.now=int(time.time())
        key=Ed25519PrivateKey.generate()
        public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        payload={"version":1,"issuer":"HANTER-LAB-ONLY","audience":"LOCAL_SYNTHETIC_ONLY",
                 "agent_id":"NCA-LOCAL-TEST","job_id":"job-lab-1","tenant_id":"lab",
                 "document_sha256":hashlib.sha256(b"fixture").hexdigest(),
                 "blueprint_sha256":hashlib.sha256(b"blueprint").hexdigest(),
                 "nonce":"a"*32,"issued_at":self.now,"expires_at":self.now+200}
        envelope={"payload":payload,"key_id":"DEMO-test",
                  "signature":key.sign(encode(payload,"DEMO-test")).hex()}
        self.queue.submit(envelope,{"DEMO-test":public},now=self.now)

    def test_real_child_process_finishes_a_synthetic_fixture(self):
        claim=self.queue.claim("worker-A",self.now,lease_seconds=15)
        result=supervise_claim(self.queue,claim,"worker-A","unused",threading.Event(),
                               lease_seconds=15,child_target=_finish_synthetic)
        self.assertEqual(result["child_exit_code"],0)
        self.assertEqual(result["job"]["state"],"LOCAL_QA_PASS")
        self.assertFalse(result["production_authorized"])
        self.assertTrue(self.queue.audit_valid())

    def test_crashed_child_claim_recovers_after_lease_with_fencing(self):
        first=self.queue.claim("worker-A",self.now,lease_seconds=15)
        result=supervise_claim(self.queue,first,"worker-A","unused",threading.Event(),
                               lease_seconds=15,child_target=_crash_synthetic)
        self.assertEqual(result["child_exit_code"],17)
        self.assertEqual(result["job"]["state"],"CLAIMED")
        second=LocalQueue(self.queue.path).claim("worker-B",first["lease_until"],lease_seconds=15)
        self.assertEqual(second["attempt"],2)
        with self.assertRaisesRegex(Rejected,"CLAIM_PROOF_REQUIRED"):
            self.queue.finish(first["job_id"],"worker-A",first["claim_token"],
                              hashlib.sha256(b"late").hexdigest(),True,first["lease_until"]+1)

    def test_local_stop_terminates_running_child_and_denies_completion(self):
        claim=self.queue.claim("worker-A",self.now,lease_seconds=30)
        marker=self.root/"child-started"
        output=[]
        thread=threading.Thread(target=lambda:output.append(supervise_claim(
            self.queue,claim,"worker-A",str(marker),threading.Event(),lease_seconds=30,
            child_target=_slow_synthetic,interval=0.05)))
        thread.start()
        deadline=time.monotonic()+8
        while not marker.exists() and time.monotonic()<deadline:
            time.sleep(0.02)
        self.assertTrue(marker.exists(),"test child did not start")
        self.queue.stop("agent","NCA-LOCAL-TEST","local test stop",int(time.time()))
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive(),"supervisor did not stop child")
        self.assertEqual(output[0]["job"]["state"],"STOPPED")
        self.assertNotEqual(output[0]["child_exit_code"],0)
        with self.assertRaises(Rejected):
            self.queue.finish(claim["job_id"],"worker-A",claim["claim_token"],
                              hashlib.sha256(b"late").hexdigest(),True,int(time.time()))

    def test_unavailable_model_leaves_task_unclaimed_and_heartbeat_stales(self):
        stop=threading.Event()
        observed=threading.Event()
        def notify(_line,**_kwargs):
            observed.set()
        thread=threading.Thread(target=run_loop,args=(self.queue,"worker-A","model",stop),
            kwargs={"poll_seconds":1,"lease_seconds":15,
                    "readiness":lambda _model:(False,"SYNTHETIC_DEPENDENCY_MISSING"),"emit":notify})
        thread.start()
        self.assertTrue(observed.wait(3))
        health=self.queue.inspect_worker("worker-A",int(time.time()),stale_after=60)
        self.assertEqual(health["status"],"WAITING_DEPENDENCIES")
        self.assertFalse(health["authenticated"])
        self.assertEqual(self.queue.inspect("job-lab-1")["state"],"PENDING")
        self.assertEqual(self.queue.inspect_worker("worker-A",health["last_seen"]+60)["status"],"STALE")
        stop.set()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(self.queue.inspect_worker("worker-A",int(time.time()))["status"],"STOPPED")

    @unittest.skipUnless(os.name=="posix","POSIX process groups required")
    def test_local_stop_signals_the_child_process_group(self):
        claim=self.queue.claim("worker-A",self.now,lease_seconds=30)
        output=[]
        thread=threading.Thread(target=lambda:output.append(supervise_claim(
            self.queue,claim,"worker-A",str(self.root),threading.Event(),lease_seconds=30,
            child_target=_slow_with_child,interval=0.03)))
        thread.start()
        deadline=time.monotonic()+8
        while not (self.root/"child-started").exists() and time.monotonic()<deadline:
            time.sleep(0.02)
        self.assertTrue((self.root/"child-started").exists())
        self.queue.stop("agent","NCA-LOCAL-TEST","local test stop",int(time.time()))
        thread.join(timeout=5)
        self.assertFalse(thread.is_alive())
        time.sleep(1.7)
        self.assertFalse((self.root/"descendant-survived").exists())
        self.assertEqual(output[0]["job"]["state"],"STOPPED")

    def test_explicit_opt_in_required_without_creating_database(self):
        env=os.environ.copy()
        env.pop("IMPERIAL_NCA_ALWAYS_ON_LAB",None)
        target=self.root/"not-created.sqlite"
        proc=subprocess.run([sys.executable,"-m","nca_control.always_on","--run-lab",
                            "--database",str(target)],env=env,capture_output=True,text=True,timeout=5)
        self.assertNotEqual(proc.returncode,0)
        self.assertFalse(target.exists())

    def test_local_admin_stop_and_resume_never_revives_stopped_jobs(self):
        base=[sys.executable,"-m","nca_control.local_admin","--database",str(self.queue.path)]
        stopped=subprocess.run(base+["stop","--scope","global","--subject","*","--reason","operator"],
                               capture_output=True,text=True,timeout=5)
        self.assertEqual(stopped.returncode,0,stopped.stderr)
        self.assertTrue(self.queue.global_stop_active())
        self.assertEqual(self.queue.inspect("job-lab-1")["state"],"STOPPED")
        resumed=subprocess.run(base+["resume","--scope","global","--subject","*"],
                               capture_output=True,text=True,timeout=5)
        self.assertEqual(resumed.returncode,0,resumed.stderr)
        self.assertFalse(self.queue.global_stop_active())
        self.assertEqual(self.queue.inspect("job-lab-1")["state"],"STOPPED")
        self.assertTrue(self.queue.audit_valid())

    def test_real_daemon_starts_reports_health_and_stops_on_sigterm(self):
        env=os.environ.copy()
        env["IMPERIAL_NCA_ALWAYS_ON_LAB"]="ALLOW_LOCAL_SYNTHETIC_ONLY"
        path=self.root/"daemon.sqlite"
        proc=subprocess.Popen([sys.executable,"-m","nca_control.always_on","--run-lab",
            "--database",str(path),"--worker-id","daemon-test","--poll-seconds","1"],
            env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+10
            status="UNKNOWN"
            while time.monotonic()<deadline and proc.poll() is None:
                if path.is_file():
                    try:
                        status=LocalQueue(path).inspect_worker("daemon-test",int(time.time()))["status"]
                    except sqlite3.Error:
                        pass
                    if status in ("WAITING_DEPENDENCIES","IDLE"):
                        break
                time.sleep(0.05)
            self.assertIn(status,("WAITING_DEPENDENCIES","IDLE"))
            proc.terminate()
            _stdout,stderr=proc.communicate(timeout=10)
            self.assertEqual(proc.returncode,0,stderr)
            self.assertEqual(LocalQueue(path).inspect_worker("daemon-test",int(time.time()))["status"],"STOPPED")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate(timeout=5)

    def test_existing_pre_lease_queue_is_migrated_without_discarding_jobs(self):
        path=self.root/"legacy.sqlite"
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE jobs(job_id TEXT PRIMARY KEY,tenant TEXT NOT NULL,agent TEXT NOT NULL,
                nonce TEXT NOT NULL UNIQUE,blueprint TEXT NOT NULL,document TEXT NOT NULL,expires INTEGER NOT NULL,
                state TEXT NOT NULL,worker TEXT,claim_digest TEXT,result_digest TEXT)""")
            db.execute("""INSERT INTO jobs VALUES('legacy','lab','agent','nonce','blueprint','doc',
                ?,'CLAIMED','old','abc',NULL)""",(self.now+100,))
        migrated=LocalQueue(path)
        self.assertEqual(migrated.inspect("legacy")["state"],"CLAIMED")
        self.assertIsNone(migrated.claim("new-worker",self.now+1))
        with sqlite3.connect(path) as db:
            columns={row[1] for row in db.execute("PRAGMA table_info(jobs)")}
        self.assertTrue({"claimed_at","lease_until","attempts"}.issubset(columns))

    def test_signed_submitter_and_loop_process_a_synthetic_fixture(self):
        path=self.root/"submitted.sqlite"
        queue=LocalQueue(path)
        env=os.environ.copy()
        env["IMPERIAL_NCA_ALWAYS_ON_LAB"]="ALLOW_LOCAL_SYNTHETIC_ONLY"
        proc=subprocess.run([sys.executable,"-m","nca_control.lab_submit","--submit-lab",
            "--database",str(path)],env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(proc.returncode,0,proc.stderr)
        submission=json.loads(proc.stdout)
        self.assertFalse(submission["owner_signature_verified"])
        self.assertFalse(submission["production_authorized"])
        self.assertEqual(queue.inspect(submission["job_id"])["state"],"PENDING")
        inspect=subprocess.run([sys.executable,"-m","nca_control.local_admin","--database",str(path),
                               "job","--job-id",submission["job_id"]],capture_output=True,text=True,timeout=5)
        self.assertEqual(inspect.returncode,0,inspect.stderr)
        self.assertEqual(json.loads(inspect.stdout)["state"],"PENDING")
        self.assertNotIn("claim_token",inspect.stdout)
        stop=threading.Event()
        thread=threading.Thread(target=run_loop,args=(queue,"worker-A","fixture",stop),
            kwargs={"poll_seconds":1,"lease_seconds":15,"readiness":lambda _:(True,"FIXTURE_ONLY"),
                    "child_target":_finish_synthetic,"emit":lambda *_a,**_k:None})
        thread.start()
        try:
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                if queue.inspect(submission["job_id"])["state"]=="LOCAL_QA_PASS":
                    break
                time.sleep(0.05)
            self.assertEqual(queue.inspect(submission["job_id"])["state"],"LOCAL_QA_PASS")
            self.assertTrue(queue.audit_valid())
        finally:
            stop.set()
            thread.join(timeout=5)
        self.assertFalse(thread.is_alive())

    def test_queue_rejects_a_symlink_path(self):
        alias=self.root/"alias.sqlite"
        alias.symlink_to(self.queue.path)
        with self.assertRaisesRegex(Rejected,"QUEUE_PATH_DENIED"):
            LocalQueue(alias)


if __name__=="__main__":
    unittest.main()
