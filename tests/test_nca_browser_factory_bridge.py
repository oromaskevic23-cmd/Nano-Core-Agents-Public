"""Cross-package offline NCA Factory → browser presence contract tests."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from nca_factory.factory import Factory
from nca_browser.factory_bridge import bind_registered_agent
from nca_browser.policy import PolicyDenied, VoiceAvatar


def blueprint(role="researcher"):
    return {
        "tenant": "enterprise-lab",
        "role": role,
        "domain": "research",
        "model": "VELION-reference-only",
        "skill": "LEGION:universal-research:v1",
        "orchestrator": "research-federated-01"
    }


class FactoryBrowserBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.factory = Factory(Path(self.tmp.name) / "factory.sqlite")
        self.factory.register("nca-web-001", blueprint(), now=100)

    def test_each_registered_agent_has_versioned_browser_profile(self):
        view = bind_registered_agent(self.factory, "nca-web-001", blueprint())
        self.assertEqual(view["blueprint_version"], 1)
        self.assertEqual(view["factory_state"], "DRAFT")
        self.assertEqual(view["browser"], "OFFLINE_DEMO_ONLY")
        self.assertEqual(view["presence"]["avatar_id"], "imperial-orb")
        self.assertEqual(view["external_reputation"], "UNRATED")
        self.assertEqual(view["accounts"], [])
        self.assertEqual(view["cloud"], [])
        self.assertFalse(view["browser_runtime_authorized"])

    def test_custom_original_avatar_and_voice(self):
        voice = VoiceAvatar(avatar_id="nca-engineer",
                            voice_style="technical-precise", locale="de-DE")
        view = bind_registered_agent(self.factory, "nca-web-001", blueprint(), voice)
        self.assertEqual(view["presence"]["avatar_id"], "nca-engineer")
        self.assertEqual(view["presence"]["locale"], "de-DE")

    def test_reprogram_makes_old_browser_configuration_stale(self):
        old = bind_registered_agent(self.factory, "nca-web-001", blueprint())
        self.factory.reprogram("nca-web-001", blueprint("engineer"), now=102)
        with self.assertRaisesRegex(PolicyDenied, "BLUEPRINT_VERSION_MISMATCH"):
            bind_registered_agent(self.factory, "nca-web-001", blueprint())
        new = bind_registered_agent(self.factory, "nca-web-001", blueprint("engineer"))
        self.assertEqual(new["blueprint_version"], 2)
        self.assertNotEqual(old["factory_evidence_digest"], new["factory_evidence_digest"])
        self.assertEqual(new["external_reputation"], "UNRATED")

    def test_owner_stop_stays_visible_and_no_runtime_claim(self):
        self.factory.stop_agent("nca-web-001", "Owner local stop", now=102)
        view = bind_registered_agent(self.factory, "nca-web-001", blueprint())
        self.assertEqual(view["factory_state"], "STOPPED")
        self.assertFalse(view["browser_runtime_authorized"])
        self.assertFalse(view["production_authorized"])

    def test_unregistered_agent_has_no_interface(self):
        with self.assertRaises(Exception):
            bind_registered_agent(self.factory, "unknown-002", blueprint())


if __name__ == "__main__":
    unittest.main()
