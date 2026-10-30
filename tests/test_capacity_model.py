"""Unit tests of arithmetic only; these do not prove scale or runtime readiness."""

import json
import subprocess
import sys
import unittest
from decimal import Decimal

from nca_lab.capacity_model import CapacityScenario


class CapacityModelTests(unittest.TestCase):
    def test_billion_registered_sparse_active(self):
        metrics = CapacityScenario(1_000_000_000, 1_000_000).calculate()
        self.assertEqual(metrics["active_fraction"], "0.001")
        self.assertEqual(metrics["logical_registry_bytes"], 512_000_000_000)
        self.assertEqual(metrics["replicated_registry_bytes_before_overhead"], 1_536_000_000_000)
        self.assertEqual(Decimal(metrics["tasks_per_second"]), Decimal(2_000_000) / Decimal(86_400))
        self.assertEqual(Decimal(metrics["heartbeat_messages_per_second"]), Decimal(1_000_000) / Decimal(300))
        self.assertEqual(Decimal(metrics["audit_events_per_second"]), Decimal(metrics["tasks_per_second"]) * 5)

    def test_dormant_registry_has_no_task_load(self):
        metrics = CapacityScenario(1_000_000_000, 0).calculate()
        self.assertEqual(Decimal(metrics["tasks_per_second"]), 0)
        self.assertEqual(Decimal(metrics["heartbeat_messages_per_second"]), 0)

    def test_zero_registry(self):
        metrics = CapacityScenario(0, 0).calculate()
        self.assertEqual(metrics["active_fraction"], "0")

    def test_full_activity(self):
        metrics = CapacityScenario(1_000_000_000, 1_000_000_000).calculate()
        self.assertEqual(metrics["active_fraction"], "1")

    def test_active_count_cannot_exceed_registry(self):
        with self.assertRaises(ValueError):
            CapacityScenario(100, 101)

    def test_invalid_negative_registry(self):
        with self.assertRaises(ValueError):
            CapacityScenario(-1, 0)

    def test_invalid_negative_active(self):
        with self.assertRaises(ValueError):
            CapacityScenario(10, -1)

    def test_invalid_negative_task_rate(self):
        with self.assertRaises(ValueError):
            CapacityScenario(10, 1, tasks_per_active_day=Decimal("-1"))

    def test_invalid_nan_task_rate(self):
        with self.assertRaises(ValueError):
            CapacityScenario(10, 1, tasks_per_active_day=Decimal("NaN"))

    def test_invalid_infinity_task_rate(self):
        with self.assertRaises(ValueError):
            CapacityScenario(10, 1, tasks_per_active_day=Decimal("Infinity"))

    def test_zero_heartbeat_rejected(self):
        with self.assertRaises(ValueError):
            CapacityScenario(10, 1, heartbeat_interval_seconds=0)

    def test_zero_replicas_rejected(self):
        with self.assertRaises(ValueError):
            CapacityScenario(10, 1, registry_replication_factor=0)

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            CapacityScenario(True, 0)

    def test_custom_rates_and_replicas(self):
        m = CapacityScenario(100, 10, tasks_per_active_day=Decimal("0.5"), heartbeat_interval_seconds=10, bytes_per_registered_record=100, audit_events_per_task=4, registry_replication_factor=2).calculate()
        self.assertEqual(m["logical_registry_bytes"], 10_000)
        self.assertEqual(m["replicated_registry_bytes_before_overhead"], 20_000)
        self.assertEqual(Decimal(m["heartbeat_messages_per_second"]), 1)
        self.assertEqual(Decimal(m["audit_events_per_second"]), Decimal(m["tasks_per_second"]) * 4)

    def test_cli_output(self):
        p = subprocess.run([sys.executable, "-m", "nca_lab.capacity_model", "--registered", "1000", "--active", "10"], capture_output=True, text=True, check=True)
        payload = json.loads(p.stdout)
        self.assertEqual(payload["estimates"]["registered_agents"], 1000)
        self.assertEqual(payload["estimates"]["active_fraction"], "0.01")


if __name__ == "__main__":
    unittest.main()
