from playwright.sync_api import Page
import os

NEIGHBOR_FEED_URL = "https://blog.naver.com/SubscriberBlogList.naver"

# 실제 확인된 셀렉터
TITLE_SELECTORS = [".se-title-text", ".pcol1"]
CONTENT_SELECTORS = [".se-main-container", ".se-section-text"]

# 댓글 관련 (로그인 상태에서만 나타나므로 앱 실행 후 확인 필요)
COMMENT_TEXTAREA_SELECTORS = [
    "textarea.u_cbox_text",
    "textarea.u_cbox_area",
    ".u_cbox_write_area textarea",
]
COMMENT_SUBMIT_SELECTORS = [
    "button.u_cbox_btn_upload",
    ".u_cbox_write_wrap button[type=button]",
]


def _resolve_target(page: Page):
    """mainFrame이 있으면 반환, 없으면 page 그대로 반환."""
    frame = page.frame(name="mainFrame")
    return frame if frame else page


def get_neighbor_post_urls(page: Page, max_count: int = 20, debug: bool = False) -> list[dict]:
    """이웃 피드에서 최신 글 URL과 제목 수집."""
    page.goto(NEIGHBOR_FEED_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    if debug:
        _dump_html(page, "debug_feed.html")

    posts = []
    seen = set()

    for _ in range(8):
        # 피드에서 블로그 글 링크 수집 (logNo 파라미터 포함된 URL)
        links = page.query_selector_all("a[href*='logNo'], a[href*='PostView']")
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                if not href or href in seen:
                    continue
                # 상대경로 보정
                if href.startswith("/"):
                    href = "https://blog.naver.com" + href

                title_el = link.query_selector(".title, .post_title, .subject, strong, span")
                title = (title_el.inner_text() if title_el else link.inner_text()).strip()
                title = title[:100]

                seen.add(href)
                posts.append({"url": href, "title": title})
                if len(posts) >= max_count:
                    return posts
            except Exception:
                continue

        page.evaluate("window.scrollBy(0, 1000)")
        page.wait_for_timeout(1200)

    return posts


def extract_post_content(page: Page, url: str, debug: bool = False) -> tuple[str, str]:
    """블로그 글 본문 텍스트와 제목 추출. (title, content) 반환."""
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)

    target = _resolve_target(page)

    if debug:
        _dump_html(page, f"debug_post_{url.split('logNo=')[-1][:10]}.html")

    title = _find_text(target, TITLE_SELECTORS)
    content = _find_text(target, CONTENT_SELECTORS)

    return title, content


def post_comment(page: Page, url: str, comment: str) -> bool:
    """댓글 입력 및 제출. 성공 여부 반환."""
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        target = _resolve_target(page)

        textarea = _find_element(target, COMMENT_TEXTAREA_SELECTORS)
        if not textarea:
            return False

        textarea.scroll_into_view_if_needed()
        textarea.click()
        textarea.fill(comment)
        page.wait_for_timeout(600)

        submit_btn = _find_element(target, COMMENT_SUBMIT_SELECTORS)
        if not submit_btn:
            return False

        submit_btn.click()
        page.wait_for_timeout(1800)
        return True
    except Exception:
        return False


def _find_text(target, selectors: list[str]) -> str:
    for sel in selectors:
        el = target.query_selector(sel)
        if el:
            text = el.inner_text().strip()
            if text:
                return text
    return ""


def _find_element(target, selectors: list[str]):
    for sel in selectors:
        el = target.query_selector(sel)
        if el:
            return el
    return None


def _dump_html(page: Page, filename: str):
    """디버그용 HTML 저장."""
    path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page.content())
    print(f"[DEBUG] HTML 저장: {path}")
