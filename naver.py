from playwright.sync_api import Page
import os

# 모바일 이웃 피드 (이웃 글만 표시됨 — PC 블로그홈은 핫토픽이 섞임)
NEIGHBOR_FEED_URL = "https://m.blog.naver.com/FeedList.naver"

# 본문 셀렉터 (검증됨 — mainFrame 내에서 동작)
TITLE_SELECTORS = [".se-title-text", ".pcol1"]
CONTENT_SELECTORS = [".se-main-container", ".se-section-text"]

# 댓글 관련 (검증됨 — 댓글 영역 열기 후 mainFrame 내에서 동작)
# 댓글 영역을 열기 위한 버튼
COMMENT_OPEN_SELECTORS = [
    ".btn_comment.pcol2._cmtList",
    "[class*='btn_comment'][class*='_cmtList']",
    "a[class*='btn_comment']",
]
# 댓글 입력란 (contenteditable div)
COMMENT_INPUT_SELECTORS = [
    "div.u_cbox_text[contenteditable='true']",
    "div.u_cbox_text.u_cbox_text_mention",
    ".u_cbox_write_area [contenteditable='true']",
]
# 등록 버튼
COMMENT_SUBMIT_SELECTORS = [
    "button.u_cbox_btn_upload",
    "button:has-text('등록')",
]


def _resolve_target(page: Page):
    """mainFrame이 있으면 반환, 없으면 page 그대로 반환."""
    frame = page.frame(name="mainFrame")
    return frame if frame else page


def get_neighbor_post_urls(page: Page, max_count: int = 20, debug: bool = False) -> list[dict]:
    """이웃새글 피드에서 최신 글 URL과 제목 수집."""
    page.goto(NEIGHBOR_FEED_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    if debug:
        _dump_html(page, "debug_feed.html")

    posts = []
    seen = set()

    for _ in range(8):
        # 모바일 피드에서 이웃 글 링크 수집 (text_area 클래스)
        links = page.query_selector_all("a[class*='text_area']")
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                if not href or href in seen:
                    continue

                # postNo 추출: URL에서 ?앞 경로의 마지막 숫자
                clean_href = href.split("?")[0].rstrip("/")
                parts = clean_href.split("/")
                if len(parts) < 2 or not parts[-1].isdigit():
                    continue

                title = link.inner_text().strip()[:100]

                # 모바일 URL → PC URL 변환
                pc_href = clean_href.replace("m.blog.naver.com", "blog.naver.com")

                seen.add(pc_href)
                posts.append({"url": pc_href, "title": title})
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
        post_id = url.rstrip("/").split("/")[-1][:10]
        _dump_html(page, f"debug_post_{post_id}.html")

    title = _find_text(target, TITLE_SELECTORS)
    content = _find_text(target, CONTENT_SELECTORS)

    return title, content


def has_my_comment(page: Page, my_blog_id: str) -> bool:
    """현재 페이지에서 내가 이미 댓글을 달았는지 확인."""
    try:
        target = _resolve_target(page)

        # 댓글 영역 열기
        open_btn = _find_visible_element(target, COMMENT_OPEN_SELECTORS)
        if open_btn:
            open_btn.scroll_into_view_if_needed()
            open_btn.click()
            page.wait_for_timeout(3000)

        # 댓글 작성자 프로필 링크에서 내 블로그 ID 검색
        comment_authors = target.query_selector_all(".u_cbox_name, [class*='u_cbox_nick']")
        for author in comment_authors:
            # 작성자 링크에 내 블로그 ID가 포함되어 있는지
            parent_link = author.evaluate_handle("el => el.closest('a')")
            if parent_link:
                href = parent_link.as_element().get_attribute("href") or ""
                if my_blog_id in href:
                    return True
            # 또는 프로필 영역의 링크 확인
            profile = author.evaluate_handle("el => el.closest('[class*=u_cbox_comment]')")
            if profile:
                profile_links = profile.as_element().query_selector_all(f"a[href*='{my_blog_id}']")
                if profile_links:
                    return True
        return False
    except Exception:
        return False


def get_my_blog_id(page: Page) -> str:
    """로그인된 사용자의 블로그 ID를 가져옴."""
    try:
        page.goto("https://blog.naver.com/MyBlog.naver", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        # 리다이렉트된 URL에서 블로그 ID 추출: https://blog.naver.com/{blogId}
        url = page.url.rstrip("/")
        blog_id = url.split("/")[-1]
        return blog_id
    except Exception:
        return ""


def post_comment(page: Page, comment: str) -> bool:
    """현재 페이지에서 댓글 입력 및 제출. extract_post_content 직후 호출할 것."""
    try:
        target = _resolve_target(page)

        # 1단계: 댓글 영역이 아직 로딩되지 않았으면 댓글 버튼 클릭
        input_el = _find_visible_element(target, COMMENT_INPUT_SELECTORS)
        if not input_el:
            open_btn = _find_visible_element(target, COMMENT_OPEN_SELECTORS)
            if open_btn:
                open_btn.scroll_into_view_if_needed()
                open_btn.click()
                page.wait_for_timeout(3000)

            input_el = _find_visible_element(target, COMMENT_INPUT_SELECTORS)
            if not input_el:
                return False

        # 2단계: placeholder 클릭으로 입력란 활성화 후 텍스트 입력
        input_el.scroll_into_view_if_needed()
        # placeholder div(u_cbox_guide)가 입력란을 덮고 있으므로 먼저 클릭
        guide = target.query_selector(".u_cbox_guide")
        if guide and guide.is_visible():
            guide.click()
            page.wait_for_timeout(500)
        else:
            # placeholder가 없으면 JS로 직접 포커스
            input_el.evaluate("el => el.focus()")
            page.wait_for_timeout(300)
        # contenteditable div에 텍스트 입력
        input_el.evaluate("(el, text) => { el.innerText = text; el.dispatchEvent(new Event('input', {bubbles: true})); }", comment)
        page.wait_for_timeout(600)

        # 3단계: 등록 버튼 클릭
        submit_btn = _find_visible_element(target, COMMENT_SUBMIT_SELECTORS)
        if not submit_btn:
            return False

        submit_btn.click()
        page.wait_for_timeout(2000)
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


def _find_visible_element(target, selectors: list[str]):
    """visible한 요소만 반환."""
    for sel in selectors:
        elements = target.query_selector_all(sel)
        for el in elements:
            try:
                if el.is_visible():
                    return el
            except Exception:
                continue
    return None


def _dump_html(page: Page, filename: str):
    """디버그용 HTML 저장."""
    path = os.path.join(os.path.expanduser("~"), "Desktop", filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page.content())
    print(f"[DEBUG] HTML 저장: {path}")
