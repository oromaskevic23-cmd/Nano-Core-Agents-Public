"""Offline NCA Browser voice, avatar, identity, cloud and navigation policy tests."""
import unittest

from nca_browser.policy import (
    AccountConnector, CloudConnector, NCAInterface, OfflineBrowserPermit,
    PolicyDenied, VoiceAvatar, check_destination_syntax
)


class NcaBrowserPolicyTests(unittest.TestCase):
    def test_default_profile_is_accessible_and_disclosed(self):
        profile = VoiceAvatar()
        self.assertEqual(profile.voice_style, "calm-professional")
        self.assertTrue(profile.text_fallback)
        self.assertEqual(profile.disclosure, "AI agent")

    def test_voice_and_avatar_allowlist(self):
        with self.assertRaises(PolicyDenied):
            VoiceAvatar(voice_style="impersonate-actor")
        with self.assertRaises(PolicyDenied):
            VoiceAvatar(avatar_id="unapproved-likeness")
        with self.assertRaises(PolicyDenied):
            VoiceAvatar(text_fallback=False)
        with self.assertRaises(PolicyDenied):
            VoiceAvatar(disclosure="human")

    def test_public_view_explicitly_no_live_browser_or_cloud(self):
        account = AccountConnector("github", "account-1", "tenant-a")
        cloud = CloudConnector("supabase", "demo-project", "tenant-a")
        view = NCAInterface("nca-1", "tenant-a", 1, account=account, cloud=cloud).public_view()
        self.assertFalse(view["real_worker"])
        self.assertFalse(view["production_authorized"])
        self.assertFalse(view["cloud_write_permission"])
        self.assertEqual(view["accounts"][0]["state"], "NOT_CONNECTED")

    def test_connectors_may_not_claim_live_connection(self):
        with self.assertRaisesRegex(PolicyDenied, "ACCOUNT_MUST_REMAIN_DISCONNECTED"):
            AccountConnector("github", "account-1", "tenant-a", state="CONNECTED")
        with self.assertRaisesRegex(PolicyDenied, "CLOUD_MUST_REMAIN_DISCONNECTED"):
            CloudConnector("supabase", "demo-project", "tenant-a", state="CONNECTED")
        with self.assertRaisesRegex(PolicyDenied, "NO_CLOUD_OPERATIONS_GRANTED"):
            CloudConnector("supabase", "demo-project", "tenant-a",
                           operations=("deploy",))

    def test_cross_tenant_connection_is_denied(self):
        account = AccountConnector("github", "account-1", "tenant-b")
        with self.assertRaisesRegex(PolicyDenied, "CROSS_TENANT"):
            NCAInterface("nca-1", "tenant-a", 1, account=account)

    def test_bad_revision_rejected(self):
        with self.assertRaisesRegex(PolicyDenied, "INVALID_BLUEPRINT_VERSION"):
            NCAInterface("nca-1", "tenant-a", True)

    def test_exact_https_host_preflight(self):
        self.assertEqual(check_destination_syntax(
            "https://example.org/products?q=test", ("example.org",)), "example.org")

    def test_url_schemes_and_userinfo_rejected(self):
        for url in ("http://example.org", "file:///etc/passwd",
                    "javascript:alert(1)", "ftp://example.org",
                    "https://user:pass@example.org/path",
                    "https://example.org:8443/", "https://example.org/#a"):
            with self.subTest(url=url):
                with self.assertRaises(PolicyDenied):
                    check_destination_syntax(url, ("example.org",))

    def test_private_and_metadata_targets_rejected(self):
        for url in ("https://localhost", "https://127.0.0.1",
                    "https://169.254.169.254", "https://10.0.0.1",
                    "https://[::1]", "https://host.local"):
            with self.subTest(url=url):
                with self.assertRaises(PolicyDenied):
                    check_destination_syntax(url, ("example.org",))

    def test_subdomain_is_not_implicitly_allowed(self):
        with self.assertRaisesRegex(PolicyDenied, "HOST_NOT_IN_ALLOWLIST"):
            check_destination_syntax("https://evil.example.org", ("example.org",))
        with self.assertRaisesRegex(PolicyDenied, "HOST_NOT_IN_ALLOWLIST"):
            check_destination_syntax("https://example.org.bad.example", ("example.org",))

    def test_non_ascii_and_punycode_hosts_rejected(self):
        with self.assertRaises(PolicyDenied):
            check_destination_syntax("https://examplé.org", ("example.org",))
        with self.assertRaises(PolicyDenied):
            check_destination_syntax("https://xn--bcher-kva.de", ("xn--bcher-kva.de",))

    def test_unapproved_network_action_always_denied(self):
        permit = OfflineBrowserPermit("nca-1", "mission-1", expires_at=120, max_steps=2)
        with self.assertRaisesRegex(PolicyDenied, "REAL_NETWORK_NAVIGATION_NOT_IMPLEMENTED"):
            permit.navigate("https://example.org")

    def test_lease_expiry_is_exclusive(self):
        permit = OfflineBrowserPermit("nca-1", "mission-1", expires_at=120, max_steps=1)
        result = permit.use_local_step(now=119)
        self.assertFalse(result["network_access"])
        with self.assertRaises(PolicyDenied):
            permit.use_local_step(now=120)

    def test_exact_lease_boundary_denied(self):
        permit = OfflineBrowserPermit("nca-1", "mission-1", expires_at=120, max_steps=1)
        with self.assertRaisesRegex(PolicyDenied, "SESSION_EXPIRED"):
            permit.use_local_step(now=120)

    def test_step_quota_blocks(self):
        permit = OfflineBrowserPermit("nca-1", "mission-1", expires_at=120, max_steps=1)
        permit.use_local_step(now=100)
        with self.assertRaisesRegex(PolicyDenied, "SESSION_QUOTA_EXCEEDED"):
            permit.use_local_step(now=101)

    def test_stop_blocks_further_use(self):
        permit = OfflineBrowserPermit("nca-1", "mission-1", expires_at=120, max_steps=2)
        permit.stop()
        with self.assertRaisesRegex(PolicyDenied, "SESSION_STOPPED"):
            permit.use_local_step(now=100)

    def test_invalid_time_or_quota(self):
        with self.assertRaises(PolicyDenied):
            OfflineBrowserPermit("nca-1", "mission-1", expires_at=0, max_steps=1)
        with self.assertRaises(PolicyDenied):
            OfflineBrowserPermit("nca-1", "mission-1", expires_at=100, max_steps=True)
        with self.assertRaises(PolicyDenied):
            OfflineBrowserPermit("nca-1", "mission-1", expires_at=100, max_steps=101)
        permit = OfflineBrowserPermit("nca-1", "mission-1", expires_at=100, max_steps=1)
        with self.assertRaises(PolicyDenied):
            permit.use_local_step(now=True)

    def test_accounts_have_no_password_fields(self):
        descriptor = AccountConnector("github", "account-reference", "tenant-a")
        self.assertEqual(set(descriptor.to_public()), {"provider", "reference", "state"})


if __name__ == "__main__":
    unittest.main()
