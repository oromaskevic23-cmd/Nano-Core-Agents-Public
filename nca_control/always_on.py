"""Supervised, single-host NCA lab loop; no production or commercial authority.

Only previously signed LOCAL_SYNTHETIC_ONLY jobs can be consumed. Local stop
and heartbeats are not a protected Owner Kill Switch or authenticated identity.
"""
from __future__ import annotations

import argparse
from http.client import HTTPConnection, HTTPException
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import signal
import sqlite3
import threading
import time

from .protocol import Rejected
from .queue import LocalQueue
from .worker import run_claimed


def runtime_readiness(model):
    """Check local prerequisites only; do not claim a task while unavailable."""
    if importlib.util.find_spec("playwright") is None:
        return False, "PLAYWRIGHT_NOT_INSTALLED"
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as driver:
            if not Path(driver.chromium.executable_path).is_file():
                return False, "CHROMIUM_NOT_INSTALLED"
    except Exception:
        return False, "CHROMIUM_NOT_AVAILABLE"
    connection = HTTPConnection("127.0.0.1",11434,timeout=3)
    try:
        connection.request("GET","/api/tags",headers={"Accept":"application/json"})
        response = connection.getresponse()
        if response.status != 200:
            return False, "LOCAL_OLLAMA_UNAVAILABLE"
        raw = response.read(256*1024+1)
        if len(raw)>256*1024:
            return False, "LOCAL_OLLAMA_RESPONSE_REJECTED"
        payload = json.loads(raw)
        if type(payload) is not dict or type(payload.get("models")) is not list:
            return False, "LOCAL_OLLAMA_RESPONSE_REJECTED"
        if not any(type(item) is dict and item.get("name")==model for item in payload["models"]):
            return False, "LOCAL_MODEL_NOT_INSTALLED"
    except (HTTPException,OSError,TimeoutError,UnicodeError,ValueError):
        return False, "LOCAL_OLLAMA_UNAVAILABLE"
    finally:
        connection.close()
    return True, "LOCAL_DEPENDENCIES_AVAILABLE"


def _job_child(path, claim, worker_id, model):
    """Dedicated child process for one fixed synthetic document only."""
    if hasattr(os,"setsid"):
        try:
            os.setsid()
        except OSError:
            pass
    from nca_runtime.__main__ import OWNED_HTML
    from nca_runtime.browser_snapshot import snapshot_owned_html
    from nca_runtime.ollama_adapter import LocalOllamaAdapter
    try:
        result=run_claimed(LocalQueue(path),claim,html=OWNED_HTML,worker_id=worker_id,
                           browser_probe=snapshot_owned_html,
                           model_call=LocalOllamaAdapter(model,timeout_seconds=90).generate,
                           clock=lambda:int(time.time()))
        print(json.dumps({"event":"LAB_CHILD_RESULT",**result},sort_keys=True),flush=True)
    except Exception:
        # Input, model responses, exception text and the claim token are not logged.
        raise SystemExit(1) from None


def _terminate_child(child, *, force=False):
    """Best-effort process-group termination on POSIX, child-only elsewhere."""
    if not child.is_alive():
        return
    if os.name == "posix":
        try:
            if os.getpgid(child.pid) == child.pid:
                os.killpg(child.pid,signal.SIGKILL if force else signal.SIGTERM)
                return
        except (ProcessLookupError,PermissionError,OSError):
            pass
    if force:
        child.kill()
    else:
        child.terminate()


def supervise_claim(queue, claim, worker_id, model, stop_event, *, lease_seconds=90,
                    child_target=_job_child, context=None, interval=0.25):
    """Fence and supervise one child; stop it on local STOP, expiry or lease loss."""
    ctx = context or multiprocessing.get_context("spawn")
    child = ctx.Process(target=child_target,args=(str(queue.path),claim,worker_id,model))
    child.start()
    next_renew = time.monotonic() + max(1,lease_seconds//3)
    next_health = time.monotonic() + 10
    reason = "CHILD_EXITED"
    try:
        while child.is_alive():
            if stop_event.wait(interval):
                reason = "SHUTDOWN_REQUESTED"
                break
            record = queue.inspect(claim["job_id"])
            if record is None or record["state"] != "CLAIMED":
                if record is not None and record["state"] in ("LOCAL_QA_PASS","LOCAL_QA_FAIL"):
                    # Let the finished child flush its sanitized evidence.
                    child.join(timeout=2)
                reason = "CLAIM_NO_LONGER_ACTIVE"
                break
            now = int(time.time())
            if now >= claim["expires_at"]:
                reason = "PERMIT_EXPIRED"
                break
            if time.monotonic() >= next_renew:
                try:
                    queue.renew(claim["job_id"],worker_id,claim["claim_token"],
                                now,lease_seconds=lease_seconds)
                except Rejected:
                    reason = "LEASE_OR_STOP_REJECTED"
                    break
                next_renew = time.monotonic() + max(1,lease_seconds//3)
            if time.monotonic() >= next_health:
                queue.report_worker(worker_id,"EXECUTING_LAB",now)
                next_health = time.monotonic()+10
    finally:
        process_group = None
        if child.is_alive():
            if os.name == "posix":
                try:
                    if os.getpgid(child.pid) == child.pid:
                        process_group = child.pid
                except (ProcessLookupError,PermissionError,OSError):
                    pass
            _terminate_child(child)
        child.join(timeout=3)
        # The group may outlive its leader (for example a browser child that
        # ignores SIGTERM), so clean it up even if the leader has already exited.
        if process_group is not None:
            try:
                os.killpg(process_group,signal.SIGKILL)
            except (ProcessLookupError,PermissionError,OSError):
                pass
        elif child.is_alive():
            _terminate_child(child,force=True)
        if child.is_alive():
            child.join(timeout=3)
    # An interrupted/failed claim remains fenced until its lease expires;
    # no early requeue while an external Ollama request might still be running.
    return {"reason":reason,"child_exit_code":child.exitcode,
            "job":queue.inspect(claim["job_id"]),"production_authorized":False}


def run_loop(queue, worker_id, model, stop_event, *, poll_seconds=15, lease_seconds=90,
             readiness=runtime_readiness, child_target=_job_child, emit=print):
    """Keep polling while this supervised host process remains alive."""
    if type(poll_seconds) is not int or not 1 <= poll_seconds <= 60:
        raise Rejected("INVALID_POLL_INTERVAL")
    if type(lease_seconds) is not int or not 15 <= lease_seconds <= 180:
        raise Rejected("INVALID_LEASE")
    # Validate before entering the loop, even when no work is available.
    queue._worker_id(worker_id)
    previous = None
    errors = 0
    try:
        while not stop_event.is_set():
            try:
                if queue.global_stop_active():
                    state, detail = "LOCAL_STOP_ENGAGED", "LOCAL_STOP"
                else:
                    ready, detail = readiness(model)
                    state = "IDLE" if ready else "WAITING_DEPENDENCIES"
                queue.report_worker(worker_id,state,int(time.time()))
                if (state,detail) != previous:
                    emit(json.dumps({"event":"LAB_WORKER_STATE","state":state,"detail":detail,
                                     "production_authorized":False}),flush=True)
                    previous = (state,detail)
                if state == "IDLE":
                    claim = queue.claim(worker_id,int(time.time()),lease_seconds=lease_seconds)
                    if claim is not None:
                        queue.report_worker(worker_id,"EXECUTING_LAB",int(time.time()))
                        result = supervise_claim(queue,claim,worker_id,model,stop_event,
                                                 lease_seconds=lease_seconds,child_target=child_target)
                        emit(json.dumps({"event":"LAB_JOB_FINISHED",**result},sort_keys=True),flush=True)
                errors = 0
                stop_event.wait(poll_seconds)
            except (Rejected,OSError,ValueError,sqlite3.Error):
                errors += 1
                emit(json.dumps({"event":"LAB_LOOP_RETRY","attempt":errors,
                                 "production_authorized":False}),flush=True)
                stop_event.wait(min(60,poll_seconds*(2**min(errors,5))))
    finally:
        queue.report_worker(worker_id,"STOPPED",int(time.time()))


def main():
    from nca_runtime.ollama_adapter import LocalOllamaAdapter
    parser=argparse.ArgumentParser(description="Supervised synthetic NCA lab worker, no production rights")
    parser.add_argument("--database",required=True,help="Local persistent SQLite queue path")
    parser.add_argument("--worker-id",default="nca-local-worker-1")
    parser.add_argument("--model",default="smollm2:1.7b-instruct-q4_K_M")
    parser.add_argument("--poll-seconds",type=int,default=15)
    parser.add_argument("--lease-seconds",type=int,default=90)
    parser.add_argument("--run-lab",action="store_true")
    args=parser.parse_args()
    if not args.run_lab or os.environ.get("IMPERIAL_NCA_ALWAYS_ON_LAB") != "ALLOW_LOCAL_SYNTHETIC_ONLY":
        parser.error("--run-lab and IMPERIAL_NCA_ALWAYS_ON_LAB=ALLOW_LOCAL_SYNTHETIC_ONLY are required")
    LocalOllamaAdapter(args.model)  # validates model identifier only; no model request
    stop_event=threading.Event()
    for sig in (signal.SIGINT,signal.SIGTERM):
        signal.signal(sig,lambda _sig,_frame:stop_event.set())
    run_loop(LocalQueue(Path(args.database)),args.worker_id,args.model,stop_event,
             poll_seconds=args.poll_seconds,lease_seconds=args.lease_seconds)


if __name__ == "__main__":
    main()
