"""One actual local Chromium page snapshot, with all HTTP requests aborted.

This is a local-owned HTML fixture, not a browser security sandbox for the web.
The result is untrusted source DATA and never an LLM instruction authority.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib

from .ollama_adapter import InferenceDenied


@dataclass(frozen=True)
class BrowserEvidence:
    heading: str
    page_text: str
    html_sha256: str
    screenshot_sha256: str
    network_block_rule: str
    actual_chromium: bool


def snapshot_owned_html(html: str) -> BrowserEvidence:
    if type(html) is not str or not 50 <= len(html) <= 20000 or "\x00" in html:
        raise InferenceDenied("INVALID_SYNTHETIC_HTML")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise InferenceDenied("PLAYWRIGHT_NOT_INSTALLED") from exc
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                service_workers="block", accept_downloads=False,
                permissions=[], java_script_enabled=False
            )
            try:
                # Not a complete network security boundary; requires additional
                # host/container egress firewall before any production external browsing.
                context.route("**/*", lambda route: route.abort("blockedbyclient"))
                page = context.new_page()
                try:
                    page.set_content(html, wait_until="load", timeout=10000)
                    headings = page.locator("h1")
                    if headings.count() != 1:
                        raise InferenceDenied("ONE_HEADING_REQUIRED")
                    heading = headings.first.inner_text().strip()
                    if not 2 <= len(heading) <= 120:
                        raise InferenceDenied("INVALID_HEADING")
                    page_text = page.locator("body").inner_text().strip()
                    if not 2 <= len(page_text) <= 2500:
                        raise InferenceDenied("INVALID_PAGE_TEXT")
                    png = page.screenshot(full_page=True, timeout=10000)
                    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
                        raise InferenceDenied("INVALID_SCREENSHOT")
                    return BrowserEvidence(
                        heading=heading, page_text=page_text,
                        html_sha256=hashlib.sha256(html.encode("utf8")).hexdigest(),
                        screenshot_sha256=hashlib.sha256(png).hexdigest(),
                        network_block_rule="ALL_REQUESTS_ABORTED_IN_BROWSER_CONTEXT",
                        actual_chromium=True,
                    )
                finally:
                    page.close()
            finally:
                context.close()
        finally:
            browser.close()
