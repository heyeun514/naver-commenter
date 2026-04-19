import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import browser
import naver
import ai
import setup

LOGIN_WAIT_SECONDS = 60
DEFAULT_MAX_NEIGHBORS = 20


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("네이버 블로그 이웃 댓글봇")
        self.geometry("620x560")
        self.resizable(True, True)
        self.minsize(500, 400)
        self._stop_flag = threading.Event()
        self._ollama_model = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}
        BG = "#2b2b2b"
        FG = "#f0f0f0"
        FRAME_BG = "#3c3c3c"
        self.configure(bg=BG)
        self.tk_setPalette(
            background=BG, foreground=FG,
            activeBackground="#555555", activeForeground=FG,
            highlightBackground=BG, highlightColor=FG,
        )

        # Ollama 상태
        status_frame = tk.Frame(self, bg=FRAME_BG, bd=1, relief="sunken")
        status_frame.pack(fill="x", **pad)
        self.ollama_label = tk.Label(status_frame, text="Ollama 상태: 확인 중...", anchor="w", bg=FRAME_BG, fg=FG)
        self.ollama_label.pack(side="left", padx=6, pady=4)
        self.install_btn = tk.Button(
            status_frame, text="설치 / 재시도", command=self._auto_setup,
            bg="#555555", fg=FG, activebackground="#666666", activeforeground=FG
        )
        self.install_btn.pack(side="right", padx=6, pady=4)

        # 설정
        config_frame = tk.LabelFrame(self, text="설정", bg=BG, fg=FG, **pad)
        config_frame.pack(fill="x", padx=12)
        tk.Label(config_frame, text="최대 이웃 수:", bg=BG, fg=FG).grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.max_var = tk.IntVar(value=DEFAULT_MAX_NEIGHBORS)
        tk.Spinbox(config_frame, from_=1, to=100, textvariable=self.max_var, width=6,
                   bg=FRAME_BG, fg=FG, buttonbackground="#555555").grid(row=0, column=1, sticky="w")

        # 로그인 카운트다운
        self.timer_label = tk.Label(self, text="", font=("", 14, "bold"), fg="#e74c3c", bg=BG)
        self.timer_label.pack(**pad)

        # 버튼
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(**pad)
        self.start_btn = tk.Button(
            btn_frame, text="시작", width=12, bg="#1a7f4b", fg="#ffffff",
            activebackground="#158a4a", activeforeground="#ffffff",
            font=("", 11, "bold"), state="disabled", command=self._start
        )
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = tk.Button(
            btn_frame, text="중지", width=12, bg="#c0392b", fg="#ffffff",
            activebackground="#a93226", activeforeground="#ffffff",
            font=("", 11, "bold"), state="disabled", command=self._stop
        )
        self.stop_btn.pack(side="left", padx=6)

        # 진행 로그
        self.log = scrolledtext.ScrolledText(self, height=16, width=62, state="disabled",
                                             font=("Courier", 11), bg=FRAME_BG, fg=FG,
                                             insertbackground=FG)
        self.log.pack(padx=12, pady=(0, 12))

        # 앱 시작 시 자동으로 환경 준비
        self.after(200, self._auto_setup)

    def _auto_setup(self):
        self.install_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.ollama_label.config(text="Ollama 상태: 준비 중...", fg="#e67e22")
        threading.Thread(target=self._run_setup, daemon=True).start()

    def _run_setup(self):
        def log_fn(msg: str, end: bool = False):
            self.after(0, lambda m=msg: self._log(m) if not end else self._log_update(m))

        ok, model = setup.ensure_ready(log_fn)
        self.after(0, lambda: self._on_setup_done(ok, model))

    def _on_setup_done(self, ok: bool, model: str):
        self.install_btn.config(state="normal")
        if ok:
            self._ollama_model = model
            self.ollama_label.config(text=f"Ollama 상태: 정상  (모델: {model})", fg="#27ae60")
            self.start_btn.config(state="normal")
            self._log(f"준비 완료. '{model}' 모델을 사용합니다.")
        else:
            self._ollama_model = None
            self.ollama_label.config(text="Ollama 설치/설정 실패 — '설치 / 재시도' 버튼을 눌러주세요", fg="#e74c3c")

    def _log(self, msg: str):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _log_update(self, msg: str):
        """마지막 줄을 덮어쓰는 진행 표시용 (다운로드 % 등)."""
        self.log.config(state="normal")
        self.log.delete("end-2l", "end-1c")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _start(self):
        if not self._ollama_model:
            messagebox.showerror("오류", "Ollama가 준비되지 않았습니다.")
            return
        self._stop_flag.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        threading.Thread(target=self._run, daemon=True).start()

    def _stop(self):
        self._stop_flag.set()
        self._log("--- 중지 요청됨 ---")

    def _wait_for_login(self, page, seconds: int):
        """로그인 감지 시 즉시 진행, 아니면 최대 seconds초 대기."""
        for i in range(seconds, 0, -1):
            if self._stop_flag.is_set():
                break
            # 로그인 성공 시 URL이 변경됨
            if "nidlogin" not in page.url:
                self.after(0, lambda: self.timer_label.config(text="로그인 완료!"))
                self._log("로그인이 감지되었습니다!")
                threading.Event().wait(2)  # 리다이렉트 완료 대기
                break
            self.after(0, lambda s=i: self.timer_label.config(text=f"로그인 대기: {s}초"))
            threading.Event().wait(1)
        self.after(0, lambda: self.timer_label.config(text=""))

    def _run(self):
        try:
            self._log("브라우저를 열고 있습니다...")
            page = browser.launch()
            page.goto("https://nid.naver.com/nidlogin.login", wait_until="domcontentloaded")
            self._log(f"네이버 로그인 페이지가 열렸습니다. {LOGIN_WAIT_SECONDS}초 안에 로그인하세요.")
            self._wait_for_login(page, LOGIN_WAIT_SECONDS)

            if self._stop_flag.is_set():
                return

            self._log("내 블로그 ID 확인 중...")
            my_blog_id = naver.get_my_blog_id(page)
            self._log(f"블로그 ID: {my_blog_id}")

            self._log("이웃 피드를 불러오는 중...")
            posts = naver.get_neighbor_post_urls(page, max_count=self.max_var.get())
            self._log(f"총 {len(posts)}개 글을 찾았습니다.")

            for i, post in enumerate(posts, 1):
                if self._stop_flag.is_set():
                    break
                url = post["url"]
                self._log(f"[{i}/{len(posts)}] 글 읽는 중: {post['title'] or url}")

                title, content = naver.extract_post_content(page, url)
                if not content:
                    self._log("  ↳ 본문을 읽지 못했습니다. 건너뜁니다.")
                    continue

                # 중복 댓글 체크
                if my_blog_id and naver.has_my_comment(page, my_blog_id):
                    self._log("  ↳ 이미 댓글을 달았습니다. 건너뜁니다.")
                    continue

                self._log("  ↳ AI로 댓글 생성 중...")
                try:
                    comment = ai.generate_comment(title or post["title"], content, model=self._ollama_model)
                except Exception as e:
                    self._log(f"  ↳ AI 오류: {e}")
                    continue

                self._log(f"  ↳ 댓글: {comment[:80]}{'...' if len(comment) > 80 else ''}")
                success = naver.post_comment(page, comment)
                self._log(f"  ↳ {'완료' if success else '댓글 입력란을 찾지 못했습니다'}")
                browser.human_delay(1.5, 3.0)

            self._log("=== 모든 작업 완료 ===")
        except Exception as e:
            self._log(f"오류 발생: {e}")
        finally:
            browser.close()
            self.after(0, lambda: self.timer_label.config(text=""))
            self.after(0, lambda: self.start_btn.config(state="normal"))
            self.after(0, lambda: self.stop_btn.config(state="disabled"))


if __name__ == "__main__":
    app = App()
    app.mainloop()
