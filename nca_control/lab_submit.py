"""Submit one signed synthetic fixture to an existing local lab queue."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from nca_runtime.__main__ import OWNED_HTML

from .protocol import Rejected, encode
from .queue import LocalQueue
from .worker import LAB_BLUEPRINT_SHA256


def main():
    parser=argparse.ArgumentParser(description="Enqueue the fixed offline NCA synthetic fixture")
    parser.add_argument("--database",required=True)
    parser.add_argument("--ttl-seconds",type=int,default=240)
    parser.add_argument("--submit-lab",action="store_true")
    args=parser.parse_args()
    if not args.submit_lab or os.environ.get("IMPERIAL_NCA_ALWAYS_ON_LAB")!="ALLOW_LOCAL_SYNTHETIC_ONLY":
        parser.error("--submit-lab and the explicit local lab opt-in are required")
    path=Path(args.database)
    if path.is_symlink() or not path.is_file():
        parser.error("an existing, non-symlink lab database is required")
    if not 15 <= args.ttl_seconds <= 300:
        parser.error("ttl-seconds must be between 15 and 300")
    timestamp=int(time.time())
    key=Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    kid="DEMO-ephemeral-submitter"
    payload={"version":1,"issuer":"HANTER-LAB-ONLY","audience":"LOCAL_SYNTHETIC_ONLY",
             "agent_id":"NCA-LOCAL-001","job_id":"lab-"+secrets.token_hex(12),
             "tenant_id":"synthetic-lab",
             "document_sha256":hashlib.sha256(OWNED_HTML.encode("utf8")).hexdigest(),
             "blueprint_sha256":LAB_BLUEPRINT_SHA256,
             "nonce":secrets.token_hex(16),"issued_at":timestamp,
             "expires_at":timestamp+args.ttl_seconds}
    envelope={"payload":payload,"key_id":kid,"signature":key.sign(encode(payload,kid)).hex()}
    try:
        LocalQueue(path).submit(envelope,{kid:public},timestamp)
    except Rejected:
        parser.exit(1,"LOCAL_LAB_SUBMISSION_REJECTED\n")
    print(json.dumps({"status":"SIGNED_LAB_JOB_QUEUED","job_id":payload["job_id"],
                      "expires_at":payload["expires_at"],"signer":"EPHEMERAL_LAB_ONLY",
                      "owner_signature_verified":False,"production_authorized":False},sort_keys=True))


if __name__=="__main__":
    main()
