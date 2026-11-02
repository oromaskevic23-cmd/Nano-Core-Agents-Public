"""Offline NCA Factory reference: no model, network, real workers or commercial authority.

Simulated exam scores are NOT authenticated reviews or public agent reputation.
SQLite SHA-256 events detect accidental changes but are not signed/a secure ledger.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time


IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED_BLUEPRINT = frozenset({"tenant", "role", "domain", "model", "skill", "orchestrator"})


class Denied(ValueError):
    """A fail-closed lifecycle transition in the offline exercise."""


def _time(now: int | None) -> int:
    value = int(time.time()) if now is None else now
    if type(value) is not int or value < 0:
        raise Denied("INVALID_TIME")
    return value


def _id(value: str) -> str:
    if type(value) is not str or not IDENTIFIER.fullmatch(value):
        raise Denied("INVALID_IDENTIFIER")
    return value


def _json(payload: object) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class Factory:
    """A small auditable lifecycle simulation; always denies production execution."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._tx() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS agents(
                  agent_id TEXT PRIMARY KEY,
                  version INTEGER NOT NULL,
                  blueprint TEXT NOT NULL,
                  digest TEXT NOT NULL,
                  state TEXT NOT NULL,
                  registered_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS revisions(
                  agent_id TEXT NOT NULL,
                  version INTEGER NOT NULL,
                  blueprint TEXT NOT NULL,
                  digest TEXT NOT NULL,
                  created_at INTEGER NOT NULL,
                  PRIMARY KEY(agent_id,version)
                );
                CREATE TABLE IF NOT EXISTS assessments(
                  agent_id TEXT NOT NULL,
                  version INTEGER NOT NULL,
                  case_id TEXT NOT NULL,
                  reviewer TEXT NOT NULL,
                  score INTEGER NOT NULL,
                  critical INTEGER NOT NULL,
                  evidence_sha TEXT NOT NULL,
                  PRIMARY KEY(agent_id,version,case_id)
                );
                CREATE TABLE IF NOT EXISTS leases(
                  agent_id TEXT PRIMARY KEY,
                  version INTEGER NOT NULL,
                  mission_id TEXT NOT NULL,
                  deadline INTEGER NOT NULL,
                  remaining INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS simulated_steps(
                  agent_id TEXT NOT NULL,
                  version INTEGER NOT NULL,
                  mission_id TEXT NOT NULL,
                  action_id TEXT NOT NULL,
                  payload_sha TEXT NOT NULL,
                  PRIMARY KEY(agent_id,version,mission_id,action_id)
                );
                CREATE TABLE IF NOT EXISTS controls(
                  scope TEXT NOT NULL,
                  subject TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  PRIMARY KEY(scope,subject)
                );
                CREATE TABLE IF NOT EXISTS audit(
                  seq INTEGER PRIMARY KEY AUTOINCREMENT,
                  entry TEXT NOT NULL,
                  previous_sha TEXT NOT NULL,
                  entry_sha TEXT NOT NULL
                );
            """)

    @contextmanager
    def _tx(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=10000")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def _event(self, db, event: dict) -> None:
        last = db.execute("SELECT entry_sha FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        previous = last["entry_sha"] if last else "0" * 64
        entry = _json(event)
        digest = hashlib.sha256((previous + "|" + entry).encode("utf8")).hexdigest()
        db.execute("INSERT INTO audit(entry,previous_sha,entry_sha) VALUES(?,?,?)",
                   (entry, previous, digest))

    def _row(self, db, agent_id: str):
        row = db.execute("SELECT * FROM agents WHERE agent_id=?", (_id(agent_id),)).fetchone()
        if row is None:
            raise Denied("UNKNOWN_AGENT")
        return row

    @staticmethod
    def _allow_controls(db, agent_id: str | None = None) -> None:
        if db.execute("SELECT 1 FROM controls WHERE scope='global' AND subject='*'").fetchone():
            raise Denied("GLOBAL_STOP")
        if agent_id and db.execute("SELECT 1 FROM controls WHERE scope='agent' AND subject=?",
                                   (agent_id,)).fetchone():
            raise Denied("AGENT_STOPPED")

    @staticmethod
    def _blueprint(value: dict) -> tuple[str, str]:
        if type(value) is not dict or set(value) != REQUIRED_BLUEPRINT:
            raise Denied("INVALID_BLUEPRINT_SCHEMA")
        for field, content in value.items():
            if type(content) is not str or not 1 <= len(content) <= 100 or not content.strip():
                raise Denied("INVALID_BLUEPRINT_FIELD_" + field.upper())
            if "\x00" in content:
                raise Denied("INVALID_BLUEPRINT_FIELD")
        source = _json(value)
        return source, hashlib.sha256(source.encode("utf8")).hexdigest()

    def register(self, agent_id: str, blueprint: dict, *, now: int | None = None) -> dict:
        agent_id = _id(agent_id)
        timestamp = _time(now)
        source, digest = self._blueprint(blueprint)
        with self._tx() as db:
            self._allow_controls(db, agent_id)
            try:
                db.execute("INSERT INTO agents VALUES (?,?,?,?,?,?)",
                           (agent_id, 1, source, digest, "DRAFT", timestamp))
                db.execute("INSERT INTO revisions VALUES (?,?,?,?,?)",
                           (agent_id, 1, source, digest, timestamp))
            except sqlite3.IntegrityError:
                raise Denied("DUPLICATE_AGENT") from None
            self._event(db, {"type": "REGISTER", "agent_id": agent_id, "version": 1,
                             "digest": digest, "at": timestamp})
        return self.inspect(agent_id)

    def start_exam(self, agent_id: str, *, now: int | None = None) -> None:
        timestamp = _time(now)
        with self._tx() as db:
            row = self._row(db, agent_id)
            self._allow_controls(db, agent_id)
            if row["state"] != "DRAFT":
                raise Denied("NOT_DRAFT")
            db.execute("UPDATE agents SET state='EXAMINING' WHERE agent_id=?", (agent_id,))
            self._event(db, {"type": "EXAM_START", "agent_id": agent_id,
                             "version": row["version"], "at": timestamp})

    def record_mock_exam(self, agent_id: str, case_id: str, reviewer: str,
                         score: int, critical: bool, evidence_sha: str,
                         *, now: int | None = None) -> None:
        """An explicitly mock assessment, NOT a signed or independent human review."""
        case_id, reviewer, timestamp = _id(case_id), _id(reviewer), _time(now)
        if type(score) is not int or not 0 <= score <= 100 or type(critical) is not bool:
            raise Denied("INVALID_SCORE")
        if type(evidence_sha) is not str or not DIGEST.fullmatch(evidence_sha):
            raise Denied("INVALID_EVIDENCE_DIGEST")
        with self._tx() as db:
            row = self._row(db, agent_id)
            self._allow_controls(db, agent_id)
            if row["state"] != "EXAMINING":
                raise Denied("NOT_EXAMINING")
            if reviewer == agent_id:
                raise Denied("SELF_REVIEW_FORBIDDEN")
            try:
                db.execute("INSERT INTO assessments VALUES(?,?,?,?,?,?,?)",
                           (agent_id, row["version"], case_id, reviewer,
                            score, int(critical), evidence_sha))
            except sqlite3.IntegrityError:
                raise Denied("DUPLICATE_EXAM_CASE") from None
            self._event(db, {"type": "MOCK_EXAM", "agent_id": agent_id,
                             "version": row["version"], "case_id": case_id,
                             "score": score, "critical": critical,
                             "evidence_sha": evidence_sha, "at": timestamp})

    def mark_candidate(self, agent_id: str, *, now: int | None = None) -> None:
        """Only promotes to OFFLINE_CANDIDATE, never to professional certification."""
        timestamp = _time(now)
        with self._tx() as db:
            row = self._row(db, agent_id)
            self._allow_controls(db, agent_id)
            if row["state"] != "EXAMINING":
                raise Denied("NOT_EXAMINING")
            aggregate = db.execute(
                "SELECT COUNT(*) n, AVG(score) avg_score, MIN(score) min_score,"
                " SUM(critical) critical_count FROM assessments WHERE agent_id=? AND version=?",
                (agent_id, row["version"])).fetchone()
            if (aggregate["n"] < 5 or aggregate["avg_score"] < 90
                    or aggregate["min_score"] < 80 or aggregate["critical_count"] != 0):
                raise Denied("EXAM_GATE_FAILED")
            db.execute("UPDATE agents SET state='OFFLINE_CANDIDATE' WHERE agent_id=?",
                       (agent_id,))
            self._event(db, {"type": "OFFLINE_CANDIDATE", "agent_id": agent_id,
                             "version": row["version"], "cases": aggregate["n"],
                             "at": timestamp})

    def open_mock_lease(self, agent_id: str, mission_id: str, duration_seconds: int,
                        max_steps: int, *, now: int | None = None) -> int:
        """Local fake mission, NO live worker process, tools, web or authority."""
        mission_id, timestamp = _id(mission_id), _time(now)
        if type(duration_seconds) is not int or not 1 <= duration_seconds <= 3600:
            raise Denied("INVALID_MISSION_TTL")
        if type(max_steps) is not int or not 1 <= max_steps <= 100:
            raise Denied("INVALID_STEP_QUOTA")
        with self._tx() as db:
            row = self._row(db, agent_id)
            self._allow_controls(db, agent_id)
            if row["state"] != "OFFLINE_CANDIDATE":
                raise Denied("NOT_OFFLINE_CANDIDATE")
            deadline = timestamp + duration_seconds
            db.execute("INSERT INTO leases VALUES (?,?,?,?,?)",
                       (agent_id, row["version"], mission_id, deadline, max_steps))
            db.execute("UPDATE agents SET state='MOCK_ACTIVE' WHERE agent_id=?", (agent_id,))
            self._event(db, {"type": "OPEN_MOCK_LEASE", "agent_id": agent_id,
                             "version": row["version"], "mission_id": mission_id,
                             "deadline": deadline, "max_steps": max_steps, "at": timestamp})
            return deadline

    def mock_step(self, agent_id: str, action_id: str, payload_sha: str,
                  *, now: int | None = None) -> dict:
        """Counts a mock step; does NOT process a prompt or execute any tool."""
        action_id, timestamp = _id(action_id), _time(now)
        if type(payload_sha) is not str or not DIGEST.fullmatch(payload_sha):
            raise Denied("INVALID_PAYLOAD_DIGEST")
        with self._tx() as db:
            row = self._row(db, agent_id)
            self._allow_controls(db, agent_id)
            if row["state"] != "MOCK_ACTIVE":
                raise Denied("NOT_MOCK_ACTIVE")
            lease = db.execute("SELECT * FROM leases WHERE agent_id=?", (agent_id,)).fetchone()
            if lease is None or lease["version"] != row["version"]:
                raise Denied("INVALID_LEASE")
            if timestamp >= lease["deadline"]:
                raise Denied("MISSION_EXPIRED")
            if lease["remaining"] < 1:
                raise Denied("TASK_QUOTA_EXCEEDED")
            try:
                db.execute("INSERT INTO simulated_steps VALUES(?,?,?,?,?)",
                           (agent_id, row["version"], lease["mission_id"],
                            action_id, payload_sha))
            except sqlite3.IntegrityError:
                raise Denied("DUPLICATE_ACTION") from None
            db.execute("UPDATE leases SET remaining=remaining-1 WHERE agent_id=?", (agent_id,))
            self._event(db, {"type": "MOCK_STEP", "agent_id": agent_id,
                             "version": row["version"], "action_id": action_id,
                             "payload_sha": payload_sha, "at": timestamp})
            return {"real_execution": False, "simulated": True,
                    "agent_id": agent_id, "action_id": action_id,
                    "remaining": lease["remaining"] - 1}

    def stop_agent(self, agent_id: str, reason: str, *, now: int | None = None) -> None:
        timestamp = _time(now)
        if type(reason) is not str or not 1 <= len(reason.strip()) <= 200:
            raise Denied("STOP_REASON_REQUIRED")
        with self._tx() as db:
            row = self._row(db, agent_id)
            db.execute("INSERT OR REPLACE INTO controls VALUES('agent',?,?)",
                       (agent_id, reason))
            db.execute("DELETE FROM leases WHERE agent_id=?", (agent_id,))
            db.execute("UPDATE agents SET state='STOPPED' WHERE agent_id=?", (agent_id,))
            self._event(db, {"type": "STOP_AGENT", "agent_id": agent_id,
                             "version": row["version"], "reason": reason, "at": timestamp})

    def stop_all(self, reason: str, *, now: int | None = None) -> None:
        timestamp = _time(now)
        if type(reason) is not str or not 1 <= len(reason.strip()) <= 200:
            raise Denied("STOP_REASON_REQUIRED")
        with self._tx() as db:
            db.execute("INSERT OR REPLACE INTO controls VALUES('global','*',?)", (reason,))
            db.execute("DELETE FROM leases")
            db.execute("UPDATE agents SET state='STOPPED'")
            self._event(db, {"type": "GLOBAL_STOP", "reason": reason, "at": timestamp})

    def reprogram(self, agent_id: str, blueprint: dict, *, now: int | None = None) -> dict:
        """Explicit local repair: new revision, old lease revoked, all QA reset."""
        timestamp = _time(now)
        source, digest = self._blueprint(blueprint)
        with self._tx() as db:
            row = self._row(db, agent_id)
            # Global stop never auto-clears; agent stop may be superseded by
            # an explicit LOCAL revision, which still has zero real authority.
            self._allow_controls(db)
            version = row["version"] + 1
            db.execute("DELETE FROM leases WHERE agent_id=?", (agent_id,))
            db.execute("DELETE FROM controls WHERE scope='agent' AND subject=?", (agent_id,))
            db.execute("UPDATE agents SET version=?, blueprint=?, digest=?, state='DRAFT'"
                       " WHERE agent_id=?", (version, source, digest, agent_id))
            db.execute("INSERT INTO revisions VALUES(?,?,?,?,?)",
                       (agent_id, version, source, digest, timestamp))
            self._event(db, {"type": "REPROGRAM", "agent_id": agent_id,
                             "from_version": row["version"], "to_version": version,
                             "digest": digest, "at": timestamp})
        return self.inspect(agent_id)

    def inspect(self, agent_id: str, *, now: int | None = None) -> dict:
        timestamp = _time(now)
        with self._tx() as db:
            row = self._row(db, agent_id)
            checks = db.execute(
                "SELECT COUNT(*) n, AVG(score) avg_score, COALESCE(SUM(critical),0) defects"
                " FROM assessments WHERE agent_id=? AND version=?",
                (agent_id, row["version"])).fetchone()
            prior = db.execute(
                "SELECT COUNT(*) n, COALESCE(SUM(critical),0) defects FROM assessments"
                " WHERE agent_id=? AND version<?", (agent_id, row["version"])).fetchone()
            lease = db.execute("SELECT * FROM leases WHERE agent_id=?", (agent_id,)).fetchone()
            stopped = db.execute("SELECT 1 FROM controls WHERE"
                                 " (scope='global' AND subject='*') OR"
                                 " (scope='agent' AND subject=?) LIMIT 1",
                                 (agent_id,)).fetchone() is not None
            state = row["state"]
            if lease is not None and timestamp >= lease["deadline"] and state == "MOCK_ACTIVE":
                state = "MOCK_EXPIRED"
            return {
                "agent_id": agent_id,
                "version": row["version"],
                "blueprint_sha256": row["digest"],
                "state": "STOPPED" if stopped else state,
                "mock_case_count": checks["n"],
                "mock_average_score": round(checks["avg_score"], 2) if checks["avg_score"] is not None else None,
                "mock_critical_defects": checks["defects"],
                "prior_revision_case_count": prior["n"],
                "prior_revision_critical_defects": prior["defects"],
                "mock_lease_deadline": lease["deadline"] if lease and not stopped else None,
                "mock_steps_remaining": lease["remaining"] if lease and not stopped else None,
                "professional_certified": False,
                "real_worker_running": False,
                "production_permitted": False,
                "external_reputation": "UNRATED",
                "source": "OFFLINE_SYNTHETIC_REFERENCE"
            }

    def audit_valid(self) -> bool:
        """Detects unintentional journal editing; no cryptographic signing."""
        with self._tx() as db:
            previous = "0" * 64
            for row in db.execute("SELECT entry,previous_sha,entry_sha FROM audit ORDER BY seq"):
                actual = hashlib.sha256((previous + "|" + row["entry"]).encode("utf8")).hexdigest()
                if row["previous_sha"] != previous or row["entry_sha"] != actual:
                    return False
                previous = actual
            return True
