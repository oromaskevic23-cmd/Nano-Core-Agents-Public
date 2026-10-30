"""Offline capacity arithmetic for prospective NCA federation designs.

NOT a benchmark, live dispatcher, cost quote, proof of operability or approval.
No network, external services, agent execution or secrets are involved.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from decimal import Decimal

SECONDS_PER_DAY = Decimal(86_400)


@dataclass(frozen=True)
class CapacityScenario:
    registered_agents: int
    active_agents: int
    tasks_per_active_day: Decimal = Decimal("2")
    heartbeat_interval_seconds: int = 300
    bytes_per_registered_record: int = 512
    audit_events_per_task: int = 5
    registry_replication_factor: int = 3

    def __post_init__(self) -> None:
        integer_fields = (
            "registered_agents", "active_agents", "heartbeat_interval_seconds",
            "bytes_per_registered_record", "audit_events_per_task",
            "registry_replication_factor",
        )
        for name in integer_fields:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.active_agents > self.registered_agents:
            raise ValueError("active_agents cannot exceed registered_agents")
        if self.heartbeat_interval_seconds == 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        if self.registry_replication_factor == 0:
            raise ValueError("registry_replication_factor must be positive")
        if not isinstance(self.tasks_per_active_day, Decimal):
            raise ValueError("tasks_per_active_day must be Decimal")
        if not self.tasks_per_active_day.is_finite() or self.tasks_per_active_day < 0:
            raise ValueError("tasks_per_active_day must be finite and nonnegative")

    def calculate(self) -> dict[str, str | int]:
        tasks_per_second = (Decimal(self.active_agents) * self.tasks_per_active_day) / SECONDS_PER_DAY
        heartbeat_messages_per_second = Decimal(self.active_agents) / Decimal(self.heartbeat_interval_seconds)
        return {
            "registered_agents": self.registered_agents,
            "active_agents": self.active_agents,
            "active_fraction": str(Decimal(self.active_agents) / Decimal(self.registered_agents)) if self.registered_agents else "0",
            "tasks_per_second": str(tasks_per_second),
            "heartbeat_messages_per_second": str(heartbeat_messages_per_second),
            "audit_events_per_second": str(tasks_per_second * self.audit_events_per_task),
            "logical_registry_bytes": self.registered_agents * self.bytes_per_registered_record,
            "replicated_registry_bytes_before_overhead": self.registered_agents * self.bytes_per_registered_record * self.registry_replication_factor,
            "assumptions": "Hypothetical steady-state rates; no peak factor, compression, indexes, partitions, backups, networking, or measured hardware capacity.",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline, hypothetical NCA capacity arithmetic (not a benchmark)")
    parser.add_argument("--registered", type=int, default=1_000_000_000)
    parser.add_argument("--active", type=int, default=1_000_000)
    parser.add_argument("--tasks-per-day", type=Decimal, default=Decimal("2"))
    parser.add_argument("--heartbeat-seconds", type=int, default=300)
    parser.add_argument("--record-bytes", type=int, default=512)
    parser.add_argument("--audit-events-per-task", type=int, default=5)
    parser.add_argument("--replicas", type=int, default=3)
    args = parser.parse_args()
    scenario = CapacityScenario(
        registered_agents=args.registered,
        active_agents=args.active,
        tasks_per_active_day=args.tasks_per_day,
        heartbeat_interval_seconds=args.heartbeat_seconds,
        bytes_per_registered_record=args.record_bytes,
        audit_events_per_task=args.audit_events_per_task,
        registry_replication_factor=args.replicas,
    )
    print(json.dumps({"scenario": {k: str(v) if isinstance(v, Decimal) else v for k, v in asdict(scenario).items()}, "estimates": scenario.calculate()}, indent=2))


if __name__ == "__main__":
    main()
