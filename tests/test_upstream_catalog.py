"""Immutable upstream evaluation policy checks. Never executes third-party code."""
from pathlib import Path
import json
import re
import unittest

CATALOG = Path(__file__).resolve().parents[1] / "third_party/evaluation/catalog.json"
EXPECTED = {
    "harness2": ("google-research/harness2", "1cfe254e8d25b15f37048c3730134686abe60335", "Apache-2.0"),
    "artemis": ("google/artemis", "351ca8422f7b5b54e80a9c1ce03a222e02415b6b", "Apache-2.0"),
    "understand-anything": ("Egonex-AI/Understand-Anything", "4e6d3299017a7432da15957874992837a315c5b4", "MIT"),
}


class UpstreamPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_deny_by_default_contract(self):
        c = self.data
        self.assertEqual(c["schema"], "imperial.third_party_evaluation.v1")
        self.assertEqual(c["policy"], "DENY_BY_DEFAULT")
        self.assertEqual(c["environment"], "EPHEMERAL_GITHUB_ACTIONS_ONLY")
        for key in ("production_installation", "production_execution",
                    "secrets_access", "paid_model_calls", "external_device_access"):
            self.assertIs(c[key], False, key)

    def test_exact_sources_and_revisions(self):
        sources = self.data["sources"]
        self.assertEqual(set(x["id"] for x in sources), set(EXPECTED))
        for item in sources:
            repository, sha, license_name = EXPECTED[item["id"]]
            self.assertEqual(item["repository"], repository)
            self.assertEqual(item["commit"], sha)
            self.assertRegex(item["commit"], r"^[a-f0-9]{40}$")
            self.assertEqual(item["license"], license_name)
            self.assertIn(item["status"], ("EXPERIMENTAL_NO_RUNTIME_AUTHORITY", "BLOCKED_ANDROID_DEVICE_REQUIRED"))

    def test_no_unbounded_install_authority(self):
        for src in self.data["sources"]:
            self.assertNotIn("PRODUCTION", src["test_level"].upper())
            self.assertFalse(any(word in src["repository"] for word in ("..", "://", "?", "@")))
            self.assertTrue(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", src["repository"]))
        self.assertEqual(len(self.data["sources"]), 3)


if __name__ == "__main__":
    unittest.main()
