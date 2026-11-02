"""Ed25519 demo-only verifier for an offline mission queue.

Never interprets these signatures as actual Owner, HANTER or AI Passport authority.
"""
import json
import re
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

DOMAIN = b"IMPERIAL-NCA-QUEUE-LAB-V1:"
FIELDS = {"version","issuer","audience","agent_id","job_id","tenant_id",
          "document_sha256","blueprint_sha256","nonce","issued_at","expires_at"}
HEX = re.compile(r"^[0-9a-f]{64}$")
NONCE = re.compile(r"^[0-9a-f]{32}$")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


class Rejected(PermissionError):
    pass


def encode(payload, key_id):
    return DOMAIN + key_id.encode("ascii") + b":" + json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def validate(envelope, trusted_keys, now):
    if type(envelope) is not dict or set(envelope) != {"payload","key_id","signature"}:
        raise Rejected("BAD_ENVELOPE")
    p = envelope["payload"]
    kid = envelope["key_id"]
    sig = envelope["signature"]
    if type(p) is not dict or set(p) != FIELDS or type(kid) is not str or not kid.startswith("DEMO-"):
        raise Rejected("BAD_SCHEMA")
    if (p["version"] != 1 or type(p["version"]) is not int or
            p["issuer"] != "HANTER-LAB-ONLY" or
            p["audience"] != "LOCAL_SYNTHETIC_ONLY"):
        raise Rejected("BAD_SCOPE")
    if any(type(p[x]) is not str or NAME.fullmatch(p[x]) is None
           for x in ("agent_id","job_id","tenant_id")):
        raise Rejected("BAD_ID")
    if any(type(p[x]) is not str or HEX.fullmatch(p[x]) is None
           for x in ("document_sha256","blueprint_sha256")):
        raise Rejected("BAD_DIGEST")
    if type(p["nonce"]) is not str or NONCE.fullmatch(p["nonce"]) is None:
        raise Rejected("BAD_NONCE")
    a, b = p["issued_at"], p["expires_at"]
    if (type(now) is not int or type(a) is not int or type(b) is not int
            or a < 0 or not a <= now < b or b-a > 300):
        raise Rejected("EXPIRED")
    pub = trusted_keys.get(kid)
    if type(pub) is not bytes or len(pub) != 32:
        raise Rejected("UNKNOWN_DEMO_KEY")
    if type(sig) is not str or re.fullmatch("[0-9a-f]{128}",sig) is None:
        raise Rejected("BAD_SIGNATURE_FORMAT")
    try:
        Ed25519PublicKey.from_public_bytes(pub).verify(bytes.fromhex(sig),encode(p,kid))
    except (InvalidSignature, ValueError, TypeError):
        raise Rejected("BAD_SIGNATURE") from None
    return dict(p)
