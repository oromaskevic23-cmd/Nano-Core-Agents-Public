"""Fail-closed, offline NCA team handoff exercise; NOT a production authorization gateway.

Project author / founding architect: Ромаскевич Александр Николаевич
International: Alexander Nikolaevich Romaskevich (RomaskevicH)
Individual code contributions: see AUTHORS.md and the Git commit history.

The registry, approval references and receipts are synthetic inputs, not authenticated
identities or independent attestations. No agent, browser, model, network or payment runs.
"""
import hashlib
import json

ACTIONS = frozenset({"RESEARCH", "CODE", "BROWSER_READ", "PUBLISH", "PAYMENT_CONFIRM"})
CLASSIFICATIONS = frozenset({"PUBLIC", "PRIVATE", "SECRET"})
REQUEST_FIELDS = frozenset({
    "task_id", "sender_id", "receiver_id", "organization_id", "workspace_id",
    "action", "classification", "browser_namespace", "approval_ref",
    "external_receipt_ref", "estimated_cost_usd", "kill_switch",
})
AGENT_FIELDS = frozenset({
    "organization_id", "workspace_id", "active", "skills", "browser_namespace",
})


def _valid_id(value):
    return isinstance(value, str) and 1 <= len(value) <= 128 and value.strip() == value


def _validate(request, registry):
    if not isinstance(request, dict) or set(request) != REQUEST_FIELDS:
        raise ValueError("REQUEST_SCHEMA_INVALID")
    if not isinstance(registry, dict) or not registry:
        raise ValueError("REGISTRY_SCHEMA_INVALID")
    for key in ("task_id", "sender_id", "receiver_id", "organization_id", "workspace_id"):
        if not _valid_id(request[key]):
            raise ValueError("REQUEST_IDENTIFIER_INVALID")
    if (not isinstance(request["action"], str) or request["action"] not in ACTIONS or
        not isinstance(request["classification"], str) or request["classification"] not in CLASSIFICATIONS):
        raise ValueError("REQUEST_ENUM_INVALID")
    if type(request["kill_switch"]) is not bool:
        raise ValueError("KILL_SWITCH_TYPE_INVALID")
    if type(request["estimated_cost_usd"]) not in (int, float) or not 0 <= request["estimated_cost_usd"] <= 1_000_000:
        raise ValueError("COST_INVALID")
    for ref in ("approval_ref", "external_receipt_ref", "browser_namespace"):
        if request[ref] is not None and not _valid_id(request[ref]):
            raise ValueError("REFERENCE_INVALID")
    for agent_id, agent in registry.items():
        if not _valid_id(agent_id) or not isinstance(agent, dict) or set(agent) != AGENT_FIELDS:
            raise ValueError("AGENT_SCHEMA_INVALID")
        if not _valid_id(agent["organization_id"]) or not _valid_id(agent["workspace_id"]):
            raise ValueError("AGENT_SCOPE_INVALID")
        if type(agent["active"]) is not bool:
            raise ValueError("AGENT_ACTIVE_INVALID")
        if not isinstance(agent["skills"], list) or any(not isinstance(skill, str) or skill not in ACTIONS for skill in agent["skills"]):
            raise ValueError("AGENT_SKILLS_INVALID")
        if agent["browser_namespace"] is not None and not _valid_id(agent["browser_namespace"]):
            raise ValueError("AGENT_BROWSER_NAMESPACE_INVALID")


def evaluate_handoff(request, registry):
    """Evaluate simulated handoff rules; never grant real authority."""
    _validate(request, registry)
    reasons = []
    sender = registry.get(request["sender_id"])
    receiver = registry.get(request["receiver_id"])
    if request["sender_id"] == request["receiver_id"]:
        reasons.append("SELF_HANDOFF")
    if sender is None or receiver is None:
        reasons.append("UNKNOWN_AGENT")
    if request["kill_switch"]:
        reasons.append("KILL_SWITCH")
    if request["estimated_cost_usd"] != 0:
        reasons.append("FREE_ONLY_COST")
    for role, agent in (("SENDER", sender), ("RECEIVER", receiver)):
        if agent is None:
            continue
        if not agent["active"]:
            reasons.append(role + "_INACTIVE")
        if agent["organization_id"] != request["organization_id"]:
            reasons.append(role + "_ORGANIZATION_BOUNDARY")
        if agent["workspace_id"] != request["workspace_id"]:
            reasons.append(role + "_WORKSPACE_BOUNDARY")
    if receiver is not None and request["action"] not in receiver["skills"]:
        reasons.append("RECEIVER_SKILL_MISSING")
    if request["classification"] == "SECRET":
        reasons.append("SECRET_HANDOFF_DENIED")
    if request["action"] == "BROWSER_READ":
        if (sender is None or receiver is None or
            request["browser_namespace"] is None or
            receiver["browser_namespace"] != request["browser_namespace"] or
            sender["browser_namespace"] == request["browser_namespace"]):
            reasons.append("BROWSER_ISOLATION")
        if len({agent["browser_namespace"] for agent in registry.values() if agent["browser_namespace"] is not None}) != sum(agent["browser_namespace"] is not None for agent in registry.values()):
            reasons.append("BROWSER_NAMESPACE_COLLISION")
    if request["action"] in ("PUBLISH", "PAYMENT_CONFIRM"):
        if request["approval_ref"] is None:
            reasons.append("APPROVAL_REQUIRED")
        if request["action"] == "PUBLISH" and request["classification"] != "PUBLIC":
            reasons.append("PUBLIC_PRIVATE_BOUNDARY")
        if request["action"] == "PAYMENT_CONFIRM" and request["external_receipt_ref"] is None:
            reasons.append("EXTERNAL_RECEIPT_REQUIRED")
    material = json.dumps({"request": request, "registry": registry, "reasons": reasons}, sort_keys=True, separators=(",", ":"))
    return {
        "decision": "SIMULATED_HOLD" if reasons else "SIMULATED_ALLOW",
        "reasons": reasons,
        "audit_sha256": hashlib.sha256(material.encode("utf-8")).hexdigest(),
        "simulation": True,
        "real_execution_allowed": False,
        "real_approvals_verified": False,
        "external_effects": 0,
    }
