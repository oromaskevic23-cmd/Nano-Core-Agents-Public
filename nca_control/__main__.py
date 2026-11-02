"""One opted-in real local Chromium + Ollama job behind a demo Ed25519 permit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from nca_runtime.__main__ import OWNED_HTML
from nca_runtime.browser_snapshot import snapshot_owned_html
from nca_runtime.ollama_adapter import LocalOllamaAdapter

from .protocol import encode
from .queue import LocalQueue
from .worker import run_one


def main():
    parser=argparse.ArgumentParser(description="One local signed-queue NCA experiment")
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--model",default="smollm2:1.7b-instruct-q4_K_M")
    args=parser.parse_args()
    if not args.live or os.environ.get("IMPERIAL_SIGNED_NCA_LAB")!="APPROVE_LOCAL_SYNTHETIC_ONLY":
        parser.error("Explicit --live and IMPERIAL_SIGNED_NCA_LAB are required")
    key=Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes(
        serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    timestamp=int(time.time())
    job_id="nca-signed-local-001"
    p={"version":1,"issuer":"HANTER-LAB-ONLY","audience":"LOCAL_SYNTHETIC_ONLY",
       "agent_id":"NCA-LOCAL-001","job_id":job_id,"tenant_id":"synthetic-lab",
       "document_sha256":hashlib.sha256(OWNED_HTML.encode()).hexdigest(),
       "blueprint_sha256":hashlib.sha256(b"demo-blueprint-v1").hexdigest(),
       "nonce":os.urandom(16).hex(),"issued_at":timestamp,"expires_at":timestamp+240}
    kid="DEMO-ephemeral-run"
    permit={"payload":p,"key_id":kid,
            "signature":key.sign(encode(p,kid)).hex()}
    with TemporaryDirectory(prefix="imperial-nca-signed-") as folder:
        queue=LocalQueue(Path(folder)/"missions.sqlite")
        queue.submit(permit,{kid:public},now=int(time.time()))
        record=run_one(
            queue,html=OWNED_HTML,worker_id="local-model-worker-1",
            browser_probe=snapshot_owned_html,
            model_call=LocalOllamaAdapter(args.model,timeout_seconds=90).generate,
            clock=lambda:int(time.time()))
        record["local_audit_valid"]=queue.audit_valid()
        record["permit_validated_by_ed25519"]=True
        record["demo_key_ephemeral"]=True
        record["model"]=args.model
        record["signed_by_actual_owner"]=False
        record["professionally_qualified"]=False
        record["paid_actions"]=0
        print(json.dumps(record,sort_keys=True,indent=2))
        if record["state"]!="LOCAL_QA_PASS" or not record["local_audit_valid"]:
            raise SystemExit("SIGNED_LOCAL_DEMO_QA_FAILED")


if __name__=="__main__":
    main()
