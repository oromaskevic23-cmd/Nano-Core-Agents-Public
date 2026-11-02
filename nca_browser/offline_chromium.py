"""Real Chromium render smoke test on synthetic HTML; outbound network blocked.

Optional dependency: Playwright + installed Chromium. No login, third-party
websites, arbitrary URLs, remote tools, real NCA or service permissions.
"""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory


def run() -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Optional Playwright is not installed; run "
            "'python -m pip install -r nca_browser/browser-requirements.txt' "
            "and 'python -m playwright install chromium' explicitly."
        ) from exc

    blocked = []

    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True)
        try:
            # Context isolation: distinct cookies/state in the same engine.
            first = browser.new_context(service_workers="block", accept_downloads=False)
            second = browser.new_context(service_workers="block", accept_downloads=False)
            try:
                def deny(route):
                    blocked.append(route.request.url)
                    route.abort("blockedbyclient")

                for context in (first, second):
                    context.route("**/*", deny)
                first.add_cookies([{
                    "name": "sandbox-marker", "value": "tenant-A",
                    "url": "https://nca-demo.invalid", "httpOnly": True,
                    "secure": True, "sameSite": "Strict"
                }])
                cookie_a = first.cookies("https://nca-demo.invalid")
                cookie_b = second.cookies("https://nca-demo.invalid")
                assert any(c["name"] == "sandbox-marker" for c in cookie_a)
                assert not any(c["name"] == "sandbox-marker" for c in cookie_b)

                page_a = first.new_page()
                page_b = second.new_page()
                try:
                    html = """<!doctype html>
                      <html lang="en"><meta charset="utf-8">
                      <title>NCA Browser / offline demo</title>
                      <main><h1>IMPERIAL NCA Browser</h1>
                      <p id="status">LOCAL SYNTHETIC RENDER</p></main></html>"""
                    page_a.set_content(html, wait_until="load")
                    page_b.set_content("<h1>Separate isolated context</h1>", wait_until="load")
                    assert page_a.locator("h1").inner_text() == "IMPERIAL NCA Browser"
                    assert page_b.locator("h1").inner_text() == "Separate isolated context"
                    with TemporaryDirectory(prefix="imperial-nca-browser-") as scratch:
                        location = Path(scratch) / "offline.png"
                        page_a.screenshot(path=str(location), full_page=True)
                        screenshot_valid = location.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
                    assert screenshot_valid

                    # Runtime network abort is exercised on a synthetic page.
                    # This is not a sufficient SSRF control for any live deployment.
                    response = page_a.evaluate("""async () => {
                      try { await fetch('https://network-prohibited.invalid/probe'); return 'UNEXPECTED'; }
                      catch (e) { return 'BLOCKED'; }
                    }""")
                    assert response == "BLOCKED"
                    assert any("network-prohibited.invalid" in url for url in blocked)
                    return {
                        "status": "REAL_CHROMIUM_OFFLINE_TEST",
                        "engine": browser.version,
                        "agent_contexts": 2,
                        "cross_context_cookies_isolated": True,
                        "synthetic_dom_rendered": True,
                        "png_screenshot_valid": screenshot_valid,
                        "synthetic_outbound_request_blocked": True,
                        "real_external_sites_opened": 0,
                        "credentialed_accounts_connected": 0,
                        "cloud_connections_operational": 0,
                        "production_browser_security_verified": False,
                    }
                finally:
                    page_a.close()
                    page_b.close()
            finally:
                first.close()
                second.close()
        finally:
            browser.close()


def main() -> None:
    print(json.dumps(run(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
