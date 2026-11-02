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
                result_digest TEXT);
            CREATE TABLE IF NOT EXISTS stops(
                scope TEXT NOT NULL, subject TEXT NOT NULL,
                reason TEXT NOT NULL, PRIMARY KEY(scope,subject));
            CREATE TABLE IF NOT EXISTS audit(
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT NOT NULL, previous TEXT NOT NULL, checksum TEXT NOT NULL);
            """)

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

    def claim(self, worker_id, now):
        if (type(worker_id) is not str or not 1 <= len(worker_id) <= 80 or
            not all(c.isalnum() or c in "._-" for c in worker_id)):
            raise Rejected("INVALID_WORKER")
        if type(now) is not int or now < 0:
            raise Rejected("INVALID_TIME")
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE jobs SET state='EXPIRED' WHERE state='PENDING' AND expires<=?",(now,))
            row = db.execute("SELECT * FROM jobs WHERE state='PENDING' ORDER BY rowid LIMIT 1").fetchone()
            if row is None:
                return None
            if self._blocked(db,row["agent"]):
                raise Rejected("STOPPED")
            token = secrets.token_hex(24)
            db.execute("UPDATE jobs SET state='CLAIMED',worker=?,claim_digest=? WHERE job_id=?",
                       (worker_id,digest(token),row["job_id"]))
            self._event(db,{"kind":"CLAIM","job":row["job_id"],"worker":worker_id,"at":now})
            return {"job_id":row["job_id"],"agent_id":row["agent"],
                    "tenant_id":row["tenant"],"blueprint_sha256":row["blueprint"],
                    "document_sha256":row["document"],"expires_at":row["expires"],
                    "claim_token":token}

    def finish(self, job_id, worker_id, token, result_sha256, qa_pass, now):
        if (type(qa_pass) is not bool or type(now) is not int or
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
