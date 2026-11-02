"""Read-only bridge from NCA Factory identity/version to NCA Browser presence.

A caller must provide the exact blueprint matching the locally registered
factory digest. This preserves version binding across reprogramming.
No real authorizations, passwords, browser sessions or cloud API calls.
"""
import hashlib
import json

from nca_factory.factory import Factory
from .policy import NCAInterface, PolicyDenied, VoiceAvatar


def _digest(blueprint: dict) -> str:
    if type(blueprint) is not dict:
        raise PolicyDenied("BLUEPRINT_REQUIRED")
    try:
        data = json.dumps(blueprint, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True)
    except (TypeError, ValueError):
        raise PolicyDenied("INVALID_BLUEPRINT") from None
    return hashlib.sha256(data.encode("utf8")).hexdigest()


def bind_registered_agent(factory: Factory, agent_id: str, blueprint: dict,
                          presence: VoiceAvatar | None = None) -> dict:
    """Return metadata for a version-bound, always-disconnected interface.

    Stops and reprogramming are reflected from the authoritative local
    registry. This function does not issue leases or revive a stopped agent.
    """
    if not isinstance(factory, Factory):
        raise PolicyDenied("FACTORY_REQUIRED")
    snapshot = factory.inspect(agent_id)
    if _digest(blueprint) != snapshot["blueprint_sha256"]:
        raise PolicyDenied("BLUEPRINT_VERSION_MISMATCH")
    tenant = blueprint.get("tenant")
    if type(tenant) is not str:
        raise PolicyDenied("TENANT_REQUIRED")
    profile = NCAInterface(
        agent_id=agent_id,
        tenant_id=tenant,
        blueprint_version=snapshot["version"],
        presence=presence if presence is not None else VoiceAvatar()
    )
    return {
        **profile.public_view(),
        "factory_state": snapshot["state"],
        "factory_evidence_digest": snapshot["blueprint_sha256"],
        "external_reputation": snapshot["external_reputation"],
        "browser_runtime_authorized": False,
        "accounts_bound": False,
        "cloud_resources_provisioned": False,
    }
