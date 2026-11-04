"""Durable SQLite queue for DEMO-only signed local NCA missions.

This process never starts a browser/model or dispatches external effects.
Stop is a local operator call, NOT authenticated Owner Kill Switch.
"""
import hashlib
import json
import secrets
import sqlite3
from pathlib import Path
from .protocol import Rejected, validate

DEFAULT_LEASE_SECONDS = 180
MAX_ATTEMPTS = 3


def digest(data):
    return hashlib.sha256(data.encode("utf8")).hexdigest()


class LocalQueue:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs(
                job_id TEXT PRIMARY KEY, tenant TEXT NOT NULL, agent TEXT NOT NULL,
                nonce TEXT NOT NULL UNIQUE, blueprint TEXT NOT NULL,
                document TEXT NOT NULL, expires INTEGER NOT NULL,
                state TEXT NOT NULL, worker TEXT, claim_digest TEXT,
                claimed_at INTEGER, lease_until INTEGER, attempts INTEGER NOT NULL DEFAULT 0,
                result_digest TEXT);
            CREATE TABLE IF NOT EXISTS stops(
                scope TEXT NOT NULL, subject TEXT NOT NULL,
                reason TEXT NOT NULL, PRIMARY KEY(scope,subject));
            CREATE TABLE IF NOT EXISTS audit(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT NOT NULL, previous TEXT NOT NULL, checksum TEXT NOT NULL);
            """)
            # Migrate existing lab queues without discarding jobs or audit history.
            # Previously claimed jobs have no reliable lease and stay fail-closed.
            db.execute("BEGIN IMMEDIATE")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
            for name, declaration in (("claimed_at", "INTEGER"), ("lease_until", "INTEGER"),
                                      ("attempts", "INTEGER NOT NULL DEFAULT 0")):
                if name not in columns:
                    db.execute(f"ALTER TABLE jobs ADD COLUMN {name} {declaration}")

    def _db(self):
        db = sqlite3.connect(self.path,timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        return db

    def _event(self, db, details):
        last = db.execute("SELECT checksum FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        prior = last["checksum"] if last else "0"*64
        event = json.dumps(details,sort_keys=True,separators=(",",":"))
        db.execute("INSERT INTO audit(event,previous,checksum) VALUES(?,?,?)",
                   (event,prior,digest(prior+"|"+event)))

    def _blocked(self, db, agent):
        return db.execute("""SELECT 1 FROM stops WHERE
                 (scope='global' AND subject='*') OR
                 (scope='agent' AND subject=?) LIMIT 1""",(agent,)).fetchone() is not None

    def submit(self, envelope, trust, now):
        p = validate(envelope, trust, now)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            if self._blocked(db,p["agent_id"]):
                raise Rejected("STOPPED")
            try:
                db.execute("""INSERT INTO jobs(job_id,tenant,agent,nonce,blueprint,
                              document,expires,state) VALUES(?,?,?,?,?,?,?,'PENDING')""",
                           (p["job_id"],p["tenant_id"],p["agent_id"],p["nonce"],
                            p["blueprint_sha256"],p["document_sha256"],p["expires_at"]))
            except sqlite3.IntegrityError:
                raise Rejected("REPLAY_OR_DUPLICATE_JOB") from None
            self._event(db,{"kind":"SUBMIT","job":p["job_id"],"nonce":p["nonce"],
                            "agent":p["agent_id"],"at":now})
        return p["job_id"]

    def _recover_expired(self, db, now):
        expired = db.execute("""SELECT job_id FROM jobs WHERE
                     state IN ('PENDING','CLAIMED') AND expires<=?""",(now,)).fetchall()
        for row in expired:
            db.execute("UPDATE jobs SET state='EXPIRED' WHERE job_id=?",(row["job_id"],))
            self._event(db,{"kind":"EXPIRE","job":row["job_id"],"at":now})
        stale = db.execute("""SELECT job_id,agent,attempts FROM jobs WHERE state='CLAIMED'
                    AND lease_until IS NOT NULL AND lease_until<=? AND expires>?""",(now,now)).fetchall()
        for row in stale:
            if self._blocked(db,row["agent"]):
                state = "STOPPED"
            elif row["attempts"] >= MAX_ATTEMPTS:
                state = "RECOVERY_EXHAUSTED"
            else:
                state = "PENDING"
            db.execute("""UPDATE jobs SET state=?,worker=NULL,claim_digest=NULL,
                       claimed_at=NULL,lease_until=NULL WHERE job_id=?""",(state,row["job_id"]))
            self._event(db,{"kind":"LEASE_RECOVERY","job":row["job_id"],
                            "state":state,"at":now})

    @staticmethod
    def _lease_seconds(value):
        if type(value) is not int or not 1 <= value <= 300:
            raise Rejected("INVALID_LEASE")
        return value

    def claim(self, worker_id, now, *, lease_seconds=DEFAULT_LEASE_SECONDS):
        if (type(worker_id) is not str or not 1 <= len(worker_id) <= 80 or
            not all(c.isalnum() or c in "._-" for c in worker_id)):
            raise Rejected("INVALID_WORKER")
        if type(now) is not int or now < 0:
            raise Rejected("INVALID_TIME")
        self._lease_seconds(lease_seconds)
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self._recover_expired(db,now)
            row = db.execute("SELECT * FROM jobs WHERE state='PENDING' ORDER BY rowid LIMIT 1").fetchone()
            if row is None:
                return None
            if self._blocked(db,row["agent"]):
                raise Rejected("STOPPED")
            token = secrets.token_hex(24)
            until = min(now+lease_seconds,row["expires"])
            db.execute("""UPDATE jobs SET state='CLAIMED',worker=?,claim_digest=?,
                       claimed_at=?,lease_until=?,attempts=attempts+1 WHERE job_id=?""",
                       (worker_id,digest(token),now,until,row["job_id"]))
            self._event(db,{"kind":"CLAIM","job":row["job_id"],"worker":worker_id,"at":now})
            return {"job_id":row["job_id"],"agent_id":row["agent"],
                    "tenant_id":row["tenant"],"blueprint_sha256":row["blueprint"],
                    "document_sha256":row["document"],"expires_at":row["expires"],
                    "claim_token":token,"lease_until":until,"attempt":row["attempts"]+1}

    def renew(self, job_id, worker_id, token, now, *, lease_seconds=DEFAULT_LEASE_SECONDS):
        self._lease_seconds(lease_seconds)
        if type(now) is not int or now < 0:
            raise Rejected("INVALID_TIME")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone()
            if row is None or row["state"] != "CLAIMED":
                raise Rejected("JOB_NOT_CLAIMED")
            if self._blocked(db,row["agent"]) or now >= row["expires"]:
                raise Rejected("STOPPED_OR_EXPIRED")
            if (row["worker"] != worker_id or not isinstance(token,str) or
                not secrets.compare_digest(row["claim_digest"],digest(token))):
                raise Rejected("CLAIM_PROOF_REQUIRED")
            if row["claimed_at"] is None or row["lease_until"] is None:
                raise Rejected("LEGACY_CLAIM_REVIEW_REQUIRED")
            if now < row["claimed_at"] or now >= row["lease_until"]:
                raise Rejected("LEASE_EXPIRED_OR_CLOCK_INVALID")
            until = min(now+lease_seconds,row["expires"])
            if until > row["lease_until"]:
                db.execute("UPDATE jobs SET lease_until=? WHERE job_id=?",(until,job_id))
                self._event(db,{"kind":"RENEW","job":job_id,"worker":worker_id,
                                "lease_until":until,"at":now})
            return {"lease_until":max(until,row["lease_until"]),"production_authorized":False}

    def finish(self, job_id, worker_id, token, result_sha256, qa_pass, now):
        if (type(qa_pass) is not bool or type(now) is not int or now < 0 or
             type(result_sha256) is not str or len(result_sha256)!=64 or
             any(c not in "0123456789abcdef" for c in result_sha256)):
            raise Rejected("INVALID_RESULT")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone()
            if row is None or row["state"]!="CLAIMED":
                raise Rejected("JOB_NOT_CLAIMED")
            if self._blocked(db,row["agent"]) or now>=row["expires"]:
                raise Rejected("STOPPED_OR_EXPIRED")
            if (row["worker"]!=worker_id or not isinstance(token,str) or
                not secrets.compare_digest(row["claim_digest"],digest(token))):
                raise Rejected("CLAIM_PROOF_REQUIRED")
            if row["claimed_at"] is None or row["lease_until"] is None:
                raise Rejected("LEGACY_CLAIM_REVIEW_REQUIRED")
            if now < row["claimed_at"] or now >= row["lease_until"]:
                raise Rejected("LEASE_EXPIRED_OR_CLOCK_INVALID")
            state = "LOCAL_QA_PASS" if qa_pass else "LOCAL_QA_FAIL"
            db.execute("UPDATE jobs SET state=?,result_digest=? WHERE job_id=?",
                       (state,result_sha256,job_id))
            self._event(db,{"kind":"COMPLETE","job":job_id,"state":state,
                            "result":result_sha256,"at":now})
            return {"state":state,"production_authorized":False,
                    "independent_human_qa":False,"real_world_actions":0}

    def stop(self, scope, subject, reason, now):
        if (scope not in ("global","agent") or type(reason) is not str or
            not 1 <= len(reason) <= 150):
            raise Rejected("INVALID_STOP")
        if scope=="global" and subject!="*":
            raise Rejected("INVALID_TARGET")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR REPLACE INTO stops VALUES(?,?,?)",(scope,subject,reason))
            if scope=="global":
                db.execute("UPDATE jobs SET state='STOPPED' WHERE state IN ('PENDING','CLAIMED')")
            else:
                db.execute("""UPDATE jobs SET state='STOPPED' WHERE agent=?
                              AND state IN ('PENDING','CLAIMED')""",(subject,))
            self._event(db,{"kind":"STOP","scope":scope,"subject":subject,"at":now})

    def inspect(self,job_id):
        with self._db() as db:
            row = db.execute("SELECT * FROM jobs WHERE job_id=?",(job_id,)).fetchone()
            return None if row is None else {
                "job_id":row["job_id"],"state":row["state"],
                "result_sha256":row["result_digest"],"production_authorized":False}

    def audit_valid(self):
        with self._db() as db:
            previous = "0"*64
            for row in db.execute("SELECT * FROM audit ORDER BY seq"):
                if row["previous"]!=previous or row["checksum"]!=digest(previous+"|"+row["event"]):
                    return False
                previous=row["checksum"]
        return True
