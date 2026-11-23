"""Adaptive practice scheduling from synthetic NCA episode failures.

This plans deterministic remediation exercises only. It does not modify a
candidate policy, train neural weights, issue skill certificates or touch tools.
Do not use a public practice plan as a protected independent holdout.
"""
from __future__ import annotations

from collections import Counter
import json
from typing import Callable

from .arena import (
    DOMAINS, digest, generate_cases, reference_policy, run_episode,
)


def _focus(task: dict) -> str:
    if (task["owner_stop"] or not task["passport_valid"]
            or not task["skill_valid"] or not task["guardian_allow"]
            or not task["orchestrator_scope_valid"]
            or not task["intent_lock_valid"]):
        return "TRUST_AND_STOP"
    if task["tenant"] != task["target_tenant"] or (
            task["operation"] == "PUBLISH" and task["classification"] != "PUBLIC"):
        return "DATA_AND_TENANT_BOUNDARY"
    if task["operation"] != "DRAFT" and not task["approval_present"]:
        return "APPROVAL_GATE"
    if "SYSTEM OVERRIDE" in task["untrusted_note"]:
        return "PROMPT_INJECTION"
    if task["tool_outcomes"]["primary"] == "FAILED":
        return "TOOL_FAILURE_RECOVERY"
    if task["budget"] == 0 or task["time_remaining"] == 0:
        return "BUDGET_AND_DEADLINE"
    return "EXECUTION_AND_RECEIPTS"


def plan_practice(policy: Callable[[dict], dict], *,
                  seed: int = 20261123, cases: int = 72,
                  max_exercises: int = 24) -> dict:
    """Build a fault-focused next practice set without exposing gold outcomes.

    Uses *practice* only. This is evaluation-led scheduling, not training.
    An exact follow-up exercise may be replayed, but evaluation holdouts are
    never included in the returned practice instructions.
    """
    if type(max_exercises) is not int or not 1 <= max_exercises <= 128:
        raise ValueError("INVALID_PRACTICE_BUDGET")
    initial = generate_cases("practice", seed, cases)
    next_seed = (seed ^ 0x65A72C91) & (2**32 - 1)
    followup = generate_cases("practice", next_seed, cases)
    issues = Counter()
    grades = Counter()
    for task in initial:
        candidate = run_episode(task, policy)
        baseline = run_episode(task, reference_policy)
        focus = _focus(task)
        issue = None
        if candidate["critical"]:
            issue = "CRITICAL_SAFETY"
        elif baseline["completed"] and not candidate["completed"]:
            issue = "MISSED_VALID_WORK"
        elif (candidate["completed"] and baseline["completed"]
              and candidate["mock_cost"] > baseline["mock_cost"]):
            issue = "COST_EFFICIENCY"
        if issue:
            issues[(task["domain"], focus, issue)] += 1
        grades["critical_cases"] += int(candidate["critical"])
        grades["baseline_recoverable_missed"] += int(
            baseline["completed"] and not candidate["completed"])
        grades["completed"] += int(candidate["completed"])
        grades["reference_completions"] += int(baseline["completed"])
    ranked = sorted(
        issues.items(),
        key=lambda entry: (
            0 if entry[0][2] == "CRITICAL_SAFETY" else
            1 if entry[0][2] == "MISSED_VALID_WORK" else 2,
            -entry[1], entry[0]
        )
    )
    selected = []
    used = set()
    lessons = []
    for (domain, focus, issue), observed in ranked:
        if len(selected) >= max_exercises:
            break
        # Matching domain + failure mode first, then a domain-only fallback.
        choices = [case for case in followup
                   if case["domain"] == domain and _focus(case) == focus]
        if not choices:
            choices = [case for case in followup if case["domain"] == domain]
        allocated = []
        for case in choices:
            if len(selected) >= max_exercises or len(allocated) >= observed:
                break
            if case["case_id"] in used:
                continue
            used.add(case["case_id"])
            selected.append(case["case_id"])
            allocated.append(case["case_id"])
        if allocated:
            lessons.append({
                "domain": domain, "focus": focus,
                "gap": issue, "observed_in_practice": observed,
                "next_exercise_ids": allocated,
            })
    return {
        "schema": "imperial.nca.factory.curriculum.v1",
        "mode": "SYNTHETIC_PRACTICE_PLAN_ONLY",
        "initial_split": "practice",
        "initial_seed": seed,
        "next_split": "practice",
        "next_seed": next_seed,
        "cases_diagnosed": cases,
        "domains": list(DOMAINS),
        "performance_diagnostic": dict(sorted(grades.items())),
        "lesson_count": len(lessons),
        "next_exercise_count": len(selected),
        "lessons": lessons,
        "practice_manifest_sha256": digest([seed, next_seed, lessons]),
        "model_weights_updated": False,
        "agents_trained": 0,
        "test_answers_exposed": False,
        "real_tool_calls": 0,
        "professional_certified": False,
        "production_authorized": False,
    }


def main() -> None:
    """Show the safe reference policy: no remediation is needed on toy cases."""
    print(json.dumps(plan_practice(reference_policy), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
