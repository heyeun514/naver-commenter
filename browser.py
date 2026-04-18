import random
import time
from playwright.sync_api import sync_playwright, Browser, Page


_playwright = None
_browser: Browser | None = None
_page: Page | None = None


def launch() -> Page:
    global _playwright, _browser, _page
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    context = _browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    )
    _page = context.new_page()
    return _page


def get_page() -> Page | None:
    return _page


def close():
    global _playwright, _browser, _page
    try:
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
    except Exception:
        pass
    _playwright = _browser = _page = None


def human_delay(min_sec: float = 1.0, max_sec: float = 3.0):
    time.sleep(random.uniform(min_sec, max_sec))
