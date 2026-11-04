"""Retake the README screenshots (screenshots/Picture1..9.png) from a running PrasiBali instance.

    python -m playwright install chromium          # once
    set SCREENSHOT_EMAIL=demo@example.com           # a verified local account, e.g. from create_demo_user
    set SCREENSHOT_PASSWORD=...
    python scripts/take_screenshots.py --base-url http://localhost:8000

Use a local instance with a dummy account only, so no real email address or personal data ends up in the images.
The order follows the product tour in README.md; the interface language is Indonesian and the theme is light.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "screenshots"
VIEWPORT = {"width": 1440, "height": 900}


def shot(page: Page, name: str, *, full_page: bool = False) -> None:
    path = OUTPUT_DIR / name
    page.screenshot(path=str(path), full_page=full_page)
    print(f"  {path.relative_to(REPO_ROOT)}")


def scroll_to(page: Page, selector: str, offset: int = 24) -> None:
    page.evaluate(
        "([sel, off]) => window.scrollTo(0, document.querySelector(sel).getBoundingClientRect().top"
        " + window.scrollY - off)",
        [selector, offset],
    )
    page.wait_for_timeout(300)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args(argv)
    email, password = os.environ.get("SCREENSHOT_EMAIL"), os.environ.get("SCREENSHOT_PASSWORD")
    if not email or not password:
        print("Set SCREENSHOT_EMAIL and SCREENSHOT_PASSWORD (a verified local account) first.", file=sys.stderr)
        return 1
    base = args.base_url.rstrip("/")
    OUTPUT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport=VIEWPORT, color_scheme="light", locale="id-ID")
        host = base.split("://", 1)[-1].split("/", 1)[0].split(":", 1)[0]
        context.add_cookies([{"name": "django_language", "value": "id", "domain": host, "path": "/"}])
        page = context.new_page()

        # 1-2. Landing page, then the features menu.
        page.goto(f"{base}/")
        shot(page, "Picture1.png", full_page=True)
        page.click("button[aria-controls=features-menu]")
        page.wait_for_selector("#features-menu:not([hidden])")
        page.wait_for_timeout(400)  # let the chevron finish rotating
        shot(page, "Picture2.png")
        page.keyboard.press("Escape")

        # 3-4. Sign up (empty form) and sign in (filled, password masked).
        page.goto(f"{base}/daftar/")
        shot(page, "Picture4.png", full_page=True)
        page.goto(f"{base}/masuk/")
        page.fill("input[name=login]", email)
        page.fill("input[name=password]", password)
        shot(page, "Picture3.png")
        page.click("form:has(input[name=login]) button[type=submit]")  # not the ID/EN forms in the navbar
        page.wait_for_load_state("networkidle")
        if "/masuk/" in page.url:
            print("Sign-in failed: check SCREENSHOT_EMAIL / SCREENSHOT_PASSWORD.", file=sys.stderr)
            return 1

        # 5. Empty workspace right after signing in (the flash message shows the dummy account).
        if "/analisis/" not in page.url:
            page.goto(f"{base}/analisis/")
        shot(page, "Picture5.png")

        # 7. A sample satua loaded into the form.
        page.click("a[href*='?contoh=']")
        page.wait_for_load_state("networkidle")
        shot(page, "Picture7.png")

        # Run the full pipeline (HTMX swaps #workspace).
        page.click("button[data-label-busy]")
        page.wait_for_selector("#analysis-result", timeout=120_000)
        page.wait_for_timeout(500)

        # 6. Whole page from input to result.
        shot(page, "Picture6.png", full_page=True)

        # 8. Highlighted story text with one character selected and its sentence context.
        scroll_to(page, "#analysis-result")
        page.locator("[data-story] button.entity").first.click()
        page.wait_for_timeout(300)
        scroll_to(page, "#analysis-result")
        shot(page, "Picture8.png")

        # 9. Character groups with their roles and the disclaimer (a taller viewport so the disclaimer fits).
        page.set_viewport_size({"width": VIEWPORT["width"], "height": 1320})
        scroll_to(page, "#groups-title")
        shot(page, "Picture9.png")
        page.set_viewport_size(VIEWPORT)

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
