"""IMPERIAL NCA Browser - offline capability policy and presentation profiles.

This module does NOT authorize real browser network, cloud access, or accounts.
All descriptors are local design fixtures. Real permissions require separate
cryptographic passports, protected orchestrators and server-side enforcement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import ipaddress
import re
from urllib.parse import urlsplit


_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,79}\Z")
_DNS = re.compile(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}\Z")
_LOCALES = frozenset({"en-US", "en-GB", "ru-RU", "uk-UA", "de-DE", "fr-FR", "es-ES", "ja-JP"})
_STYLES = frozenset({"calm-professional", "warm-professional", "technical-precise", "concise-executive"})
_AVATARS = frozenset({"imperial-orb", "nca-architect", "nca-researcher", "nca-engineer", "nca-guardian"})
_STATES = frozenset({"NOT_CONNECTED", "PENDING_APPROVAL", "REVOKED"})


class PolicyDenied(ValueError):
    """Fail-closed decision in the offline architecture prototype."""


def _id(value: str, field_name: str = "identifier") -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise PolicyDenied("INVALID_" + field_name.upper())
    return value


def _host(value: str) -> str:
    if type(value) is not str or not _DNS.fullmatch(value) or len(value) > 253:
        raise PolicyDenied("INVALID_HOST")
    if value.startswith("xn--") or ".xn--" in value:
        # Internationalized hosts may be permitted later only with IDNA
        # validation and domain risk checks.
        raise PolicyDenied("INTERNATIONALIZED_HOST_REVIEW_REQUIRED")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    raise PolicyDenied("IP_LITERALS_FORBIDDEN")


@dataclass(frozen=True)
class VoiceAvatar:
    avatar_id: str = "imperial-orb"
    voice_style: str = "calm-professional"
    locale: str = "en-US"
    text_fallback: bool = True
    disclosure: str = "AI agent"

    def __post_init__(self):
        if self.avatar_id not in _AVATARS:
            raise PolicyDenied("UNKNOWN_AVATAR")
        if self.voice_style not in _STYLES or self.locale not in _LOCALES:
            raise PolicyDenied("INVALID_VOICE_PROFILE")
        if self.text_fallback is not True or self.disclosure != "AI agent":
            raise PolicyDenied("ACCESSIBILITY_OR_DISCLOSURE_REQUIRED")

    def to_public(self) -> dict:
        return {"avatar_id": self.avatar_id, "voice_style": self.voice_style,
                "locale": self.locale, "text_fallback": self.text_fallback,
                "disclosure": self.disclosure}


@dataclass(frozen=True)
class AccountConnector:
    provider: str
    reference: str
    tenant_id: str
    state: str = "NOT_CONNECTED"
    # No secrets, passwords, cookies or access tokens belong in this object.

    def __post_init__(self):
        _id(self.provider, "provider")
        _id(self.reference, "account_reference")
        _id(self.tenant_id, "tenant")
        if self.state not in _STATES:
            raise PolicyDenied("ACCOUNT_MUST_REMAIN_DISCONNECTED_IN_OFFLINE_DEMO")

    def to_public(self) -> dict:
        return {"provider": self.provider, "reference": self.reference, "state": self.state}


@dataclass(frozen=True)
class CloudConnector:
    provider: str
    resource_reference: str
    tenant_id: str
    state: str = "NOT_CONNECTED"
    operations: tuple[str, ...] = ()
    # Live cloud writes must be explicitly authorized in a private service.

    def __post_init__(self):
        _id(self.provider, "provider")
        _id(self.resource_reference, "resource_reference")
        _id(self.tenant_id, "tenant")
        if self.state not in _STATES:
            raise PolicyDenied("CLOUD_MUST_REMAIN_DISCONNECTED_IN_OFFLINE_DEMO")
        if self.operations:
            raise PolicyDenied("NO_CLOUD_OPERATIONS_GRANTED")


@dataclass(frozen=True)
class NCAInterface:
    agent_id: str
    tenant_id: str
    blueprint_version: int
    presence: VoiceAvatar = field(default_factory=VoiceAvatar)
    account: AccountConnector | None = None
    cloud: CloudConnector | None = None

    def __post_init__(self):
        _id(self.agent_id, "agent")
        _id(self.tenant_id, "tenant")
        if type(self.blueprint_version) is not int or self.blueprint_version < 1:
            raise PolicyDenied("INVALID_BLUEPRINT_VERSION")
        for connector in (self.account, self.cloud):
            if connector and connector.tenant_id != self.tenant_id:
                raise PolicyDenied("CROSS_TENANT_CONNECTOR")

    def public_view(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "blueprint_version": self.blueprint_version,
            "presence": self.presence.to_public(),
            "accounts": [self.account.to_public()] if self.account else [],
            "cloud": ([{"provider": self.cloud.provider,
                       "resource_reference": self.cloud.resource_reference,
                       "state": self.cloud.state}] if self.cloud else []),
            "browser": "OFFLINE_DEMO_ONLY",
            "real_worker": False,
            "voice_audio_available": "client-device-dependent",
            "cloud_write_permission": False,
            "production_authorized": False,
        }


def check_destination_syntax(url: str, allowed_hostnames: tuple[str, ...]) -> str:
    """Preflight URL syntax only. NEVER a real-network security guarantee.

    Live service additionally requires DNS pinning + network egress firewall
    against SSRF, redirects, private addresses and platform restrictions.
    """
    if type(url) is not str or not 1 <= len(url) <= 2048 or any(
        ord(character) < 33 or ord(character) > 126 for character in url
    ):
        raise PolicyDenied("INVALID_URL")
    if type(allowed_hostnames) is not tuple or not allowed_hostnames:
        raise PolicyDenied("EMPTY_ALLOWLIST")
    for host in allowed_hostnames:
        _host(host)
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise PolicyDenied("MALFORMED_URL") from None
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password:
        raise PolicyDenied("HTTPS_ONLY_NO_USERINFO")
    if port not in (None, 443) or parts.fragment:
        raise PolicyDenied("URL_PORT_OR_FRAGMENT_NOT_ALLOWED")
    host = parts.hostname
    if not host:
        raise PolicyDenied("MISSING_HOST")
    host = _host(host)
    if host not in allowed_hostnames:
        raise PolicyDenied("HOST_NOT_IN_ALLOWLIST")
    return host


class OfflineBrowserPermit:
    """Finite local session counters. Never starts or grants web connectivity."""

    def __init__(self, agent_id: str, mission_id: str, expires_at: int, max_steps: int):
        self.agent_id = _id(agent_id, "agent")
        self.mission_id = _id(mission_id, "mission")
        if type(expires_at) is not int or expires_at <= 0:
            raise PolicyDenied("INVALID_EXPIRES_AT")
        if type(max_steps) is not int or not 1 <= max_steps <= 100:
            raise PolicyDenied("INVALID_STEP_COUNT")
        self.expires_at = expires_at
        self.remaining = max_steps
        self.stopped = False

    def use_local_step(self, now: int) -> dict:
        if type(now) is not int or now < 0:
            raise PolicyDenied("INVALID_NOW")
        if self.stopped:
            raise PolicyDenied("SESSION_STOPPED")
        if now >= self.expires_at:
            raise PolicyDenied("SESSION_EXPIRED")
        if self.remaining < 1:
            raise PolicyDenied("SESSION_QUOTA_EXCEEDED")
        self.remaining -= 1
        return {"simulated": True, "network_access": False,
                "agent_id": self.agent_id, "remaining": self.remaining}

    def stop(self) -> None:
        self.stopped = True

    def navigate(self, *_args, **_kwargs):
        raise PolicyDenied("REAL_NETWORK_NAVIGATION_NOT_IMPLEMENTED")
