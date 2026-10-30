#!/usr/bin/env python3
"""Deterministic synthetic NCA gate exercises. No model, agents, or external effects."""
from collections import Counter
import argparse
import hashlib
import itertools
import json
import random

ACTIONS = ("DRAFT", "DISPATCH", "PUBLISH", "PAYMENT_CONFIRM")
CLASSIFICATIONS = ("PUBLIC", "PRIVATE", "SECRET")
FLAGS = ("passport", "skill", "guardian", "domain", "approval", "kill", "external_receipt")
FIELDS = set(FLAGS) | {"action", "classification"}


def evaluate(case):
    """Return a simulated exercise decision; input assertions are not real authority."""
    if not isinstance(case, dict) or set(case) != FIELDS:
        raise ValueError("CASE_SCHEMA_INVALID")
    if case["action"] not in ACTIONS or case["classification"] not in CLASSIFICATIONS:
        raise ValueError("CASE_ENUM_INVALID")
    if any(type(case[name]) is not bool for name in FLAGS):
        raise ValueError("CASE_FLAG_INVALID")
    reasons = []
    if case["kill"]:
        reasons.append("KILL_SWITCH")
    for flag in ("passport", "skill", "guardian", "domain"):
        if not case[flag]:
            reasons.append("MISSING_" + flag.upper())
    if case["action"] != "DRAFT" and not case["approval"]:
        reasons.append("MISSING_APPROVAL")
    if case["action"] == "PUBLISH" and case["classification"] != "PUBLIC":
        reasons.append("CLASSIFICATION_BOUNDARY")
    if case["action"] == "PAYMENT_CONFIRM" and not case["external_receipt"]:
        reasons.append("MISSING_EXTERNAL_RECEIPT")
    return {"decision": "SIMULATED_HOLD" if reasons else "SIMULATED_ALLOW",
            "reasons": reasons, "simulation": True, "real_execution_allowed": False}


def oracle(case):
    """Independent boolean statement of the exercise rules for simulation checking."""
    common = (not case["kill"] and case["passport"] and case["skill"]
              and case["guardian"] and case["domain"])
    action_approved = case["action"] == "DRAFT" or case["approval"]
    safe_publication = case["action"] != "PUBLISH" or case["classification"] == "PUBLIC"
    receipt_available = case["action"] != "PAYMENT_CONFIRM" or case["external_receipt"]
    return common and action_approved and safe_publication and receipt_available


def run(cases, seed):
    if type(cases) is not int or not 1 <= cases <= 1_000_000:
        raise ValueError("CASES_OUT_OF_RANGE")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("SEED_OUT_OF_RANGE")
    rng = random.Random(seed)
    counts = Counter()
    digest = hashlib.sha256()
    mismatches = 0
    for _ in range(cases):
        case = {name: bool(rng.getrandbits(1)) for name in FLAGS}
        case["action"] = rng.choice(ACTIONS)
        case["classification"] = rng.choice(CLASSIFICATIONS)
        result = evaluate(case)
        allowed = result["decision"] == "SIMULATED_ALLOW"
        mismatches += allowed != oracle(case)
        counts[result["decision"]] += 1
        # Digest each input and output so the run can be compared without retaining records.
        digest.update(json.dumps([case, result["decision"]], sort_keys=True, separators=(",", ":")).encode())
        digest.update(b"\n")
    return {"simulation": True, "cases": cases, "seed": seed, "decisions": dict(sorted(counts.items())),
            "oracle_mismatches": mismatches, "case_stream_sha256": digest.hexdigest(),
            "agents_trained": 0, "real_executions": 0, "external_effects": 0,
            "scope": "SYNTHETIC_POLICY_EXERCISE_ONLY"}


def exhaustive_check():
    """Exhaust the finite mock gate matrix independently of the random run."""
    count = 0
    for values in itertools.product((False, True), repeat=len(FLAGS)):
        for action, classification in itertools.product(ACTIONS, CLASSIFICATIONS):
            case = dict(zip(FLAGS, values)) | {"action": action, "classification": classification}
            if (evaluate(case)["decision"] == "SIMULATED_ALLOW") != oracle(case):
                raise AssertionError("EXHAUSTIVE_MISMATCH")
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20261030)
    args = parser.parse_args()
    result = run(args.cases, args.seed)
    result["exhaustive_gate_combinations"] = exhaustive_check()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["oracle_mismatches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
