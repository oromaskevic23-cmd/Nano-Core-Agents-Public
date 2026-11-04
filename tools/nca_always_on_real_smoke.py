"""One explicit real-browser/local-model lab proof on an ephemeral test host."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

from nca_control.queue import LocalQueue


def wait_for(check, timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        try:
            value=check()
            if value:
                return value
        except (OSError,sqlite3.Error):
            pass
        time.sleep(0.5)
    raise RuntimeError("LOCAL_LAB_TIMEOUT")


def main():
    if os.environ.get("IMPERIAL_NCA_ALWAYS_ON_LAB")!="ALLOW_LOCAL_SYNTHETIC_ONLY":
        raise SystemExit("Explicit local synthetic lab opt-in is required")
    env=os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="nca-real-always-on-") as folder:
        root=Path(folder)
        database=root/"queue.sqlite"
        with (root/"daemon.log").open("w+",encoding="utf8") as output:
            worker=subprocess.Popen([sys.executable,"-m","nca_control.always_on","--run-lab",
                "--database",str(database),"--worker-id","real-lab-worker","--poll-seconds","1",
                "--lease-seconds","60"],env=env,stdout=output,stderr=subprocess.STDOUT)
            try:
                def ready():
                    if worker.poll() is not None:
                        raise RuntimeError("DAEMON_EXITED")
                    if database.is_file():
                        status=LocalQueue(database).inspect_worker("real-lab-worker",int(time.time()))
                        return status["status"]=="IDLE"
                    return False
                wait_for(ready,45)
                submission=subprocess.run([sys.executable,"-m","nca_control.lab_submit","--submit-lab",
                    "--database",str(database)],env=env,capture_output=True,text=True,timeout=10,check=True)
                task=json.loads(submission.stdout)
                def finished():
                    if worker.poll() is not None:
                        raise RuntimeError("DAEMON_EXITED")
                    record=LocalQueue(database).inspect(task["job_id"])
                    if record and record["state"] not in {"PENDING","CLAIMED"}:
                        return record
                    return False
                record=wait_for(finished,210)
                if record["state"]!="LOCAL_QA_PASS":
                    raise RuntimeError("LOCAL_QA_DID_NOT_PASS")
                def child_evidence():
                    output.flush()
                    lines=(root/"daemon.log").read_text(encoding="utf8").splitlines()
                    parsed=[json.loads(line) for line in lines if line.startswith("{")]
                    matches=[x for x in parsed if x.get("event")=="LAB_CHILD_RESULT"
                             and x.get("job_id")==task["job_id"]]
                    return matches[-1] if matches else False
                evidence=wait_for(child_evidence,5)
                if (evidence["state"]!="LOCAL_QA_PASS" or evidence["browser_real_chromium"] is not True
                    or evidence["actual_model_call_reported"] is not True
                    or evidence["signed_ai_passport_verified"] is not False
                    or evidence["independent_human_qa"] is not False
                    or evidence["production_authorized"] is not False):
                    raise RuntimeError("LAB_EVIDENCE_MISMATCH")
                if not LocalQueue(database).audit_valid():
                    raise RuntimeError("LOCAL_AUDIT_CHAIN_INVALID")
                worker.terminate()
                worker.wait(timeout=15)
                status=LocalQueue(database).inspect_worker("real-lab-worker",int(time.time()))
                if worker.returncode!=0 or status["status"]!="STOPPED":
                    raise RuntimeError("GRACEFUL_STOP_NOT_VERIFIED")
                print(json.dumps({"status":"REAL_SYNTHETIC_LAB_CYCLE_COMPLETE",
                    "real_chromium":True,"local_ollama_response":True,
                    "qa":"DETERMINISTIC_LOCAL_ONLY","local_audit_chain_valid":True,
                    "graceful_stop":True,"owner_passport":"NOT_VERIFIED",
                    "independent_human_qa":False,"continuous_hosting":"NOT_VERIFIED",
                    "production_authorized":False},sort_keys=True))
            finally:
                if worker.poll() is None:
                    worker.terminate()
                    try:
                        worker.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        worker.kill()
                        worker.wait(timeout=5)
                if sys.exc_info()[0] is not None:
                    output.flush()
                    print((root/"daemon.log").read_text(encoding="utf8")[-8000:],file=sys.stderr)


if __name__=="__main__":
    main()
