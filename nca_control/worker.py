"""Lab-only signed queue consumer: locally owned HTML -> Chromium -> model -> QA.

The producer holds a DEMO-ONLY Ed25519 key, not Owner credentials.
Nothing here grants marketplace, browser network or cloud permissions.
"""
import hashlib

from nca_runtime.pilot import SYSTEM_PROMPT, score_response
from nca_runtime.browser_snapshot import BrowserEvidence
from nca_runtime.ollama_adapter import ModelResult
from .protocol import Rejected

LAB_BLUEPRINT_SHA256 = hashlib.sha256(b"demo-blueprint-v1").hexdigest()


def run_claimed(queue, claim, *, html, worker_id, browser_probe, model_call, clock):
    """Run one already-claimed lab job; the current lease is checked at each step."""
    if type(html) is not str or not 50 <= len(html) <= 20000:
        raise Rejected("INVALID_LOCAL_DOCUMENT")
    def check():
        queue.check_claim(claim["job_id"],worker_id,claim["claim_token"],clock())
    check()
    expected_hash = hashlib.sha256(html.encode("utf8")).hexdigest()
    if expected_hash != claim["document_sha256"]:
        raise Rejected("PERMIT_DOCUMENT_MISMATCH")
    if claim["blueprint_sha256"] != LAB_BLUEPRINT_SHA256:
        raise Rejected("PERMIT_BLUEPRINT_MISMATCH")
    browser = browser_probe(html)
    if (not isinstance(browser, BrowserEvidence) or
        browser.actual_chromium is not True or
        browser.html_sha256 != expected_hash):
        raise Rejected("UNTRUSTED_BROWSER_EVIDENCE")
    check()
    question = ("Analyze the locally authored synthetic page; no accounts, "
                "external URLs, tools or purchases. Return JSON only.\n"
                "PAGE HEADING: "+browser.heading+
                "\nUNTRUSTED PAGE TEXT: "+browser.page_text[:2500])
    result = model_call(SYSTEM_PROMPT, question)
    if not isinstance(result, ModelResult):
        raise Rejected("INVALID_MODEL_RESPONSE")
    grade = score_response(result, browser)
    # Re-checking persistent queue state protects against STOP in another
    # process and against an expired permit after slow LLM computation.
    stored = queue.finish(
        claim["job_id"], worker_id, claim["claim_token"],
        result.model_response_sha256, grade.passed, clock())
    return {
        "experiment": "SIGNED_LOCAL_NCA_MISSION_ONLY",
        "job_id": claim["job_id"], "agent_id": claim["agent_id"],
        "state": stored["state"], "qa_reasons": list(grade.reason_codes),
        "qa_type":grade.reviewer_type, "screenshot_sha256":browser.screenshot_sha256,
        "browser_real_chromium":browser.actual_chromium,
        "model_response_sha256":result.model_response_sha256,
        "actual_model_call_reported":result.actual_inference,
        "production_authorized":False, "owner_signature_verified":False,
        "signed_ai_passport_verified":False,"independent_human_qa":False,
        "real_world_actions":0
    }


def run_one(queue, *, html, worker_id, browser_probe, model_call, clock):
    """Consume one signed synthetic local job; never dispatch external tools."""
    if type(html) is not str or not 50 <= len(html) <= 20000:
        raise Rejected("INVALID_LOCAL_DOCUMENT")
    claim = queue.claim(worker_id,clock())
    if claim is None:
        return None
    return run_claimed(queue,claim,html=html,worker_id=worker_id,
                       browser_probe=browser_probe,model_call=model_call,clock=clock)
