import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

import browser
import naver
import ai
import setup

LOGIN_WAIT_SECONDS = 30
DEFAULT_MAX_NEIGHBORS = 20


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("네이버 블로그 이웃 댓글봇")
        self.resizable(False, False)
        self._stop_flag = threading.Event()
        self._ollama_model = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # Ollama 상태
        status_frame = tk.Frame(self, bd=1, relief="sunken")
        status_frame.pack(fill="x", **pad)
        self.ollama_label = tk.Label(status_frame, text="Ollama 상태: 확인 중...", anchor="w")
        self.ollama_label.pack(side="left", padx=6, pady=4)
        self.install_btn = tk.Button(
            status_frame, text="설치 / 재시도", command=self._auto_setup
        )
        self.install_btn.pack(side="right", padx=6, pady=4)

        # 설정
        config_frame = tk.LabelFrame(self, text="설정", **pad)
        config_frame.pack(fill="x", padx=12)
        tk.Label(config_frame, text="최대 이웃 수:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.max_var = tk.IntVar(value=DEFAULT_MAX_NEIGHBORS)
        tk.Spinbox(config_frame, from_=1, to=100, textvariable=self.max_var, width=6).grid(row=0, column=1, sticky="w")

        # 로그인 카운트다운
        self.timer_label = tk.Label(self, text="", font=("", 14, "bold"), fg="#e74c3c")
        self.timer_label.pack(**pad)

        # 버튼
        btn_frame = tk.Frame(self)
        btn_frame.pack(**pad)
        self.start_btn = tk.Button(
            btn_frame, text="시작", width=12, bg="#2ecc71", fg="white",
            state="disabled", command=self._start
        )
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = tk.Button(
            btn_frame, text="중지", width=12, bg="#e74c3c", fg="white",
            state="disabled", command=self._stop
        )
        self.stop_btn.pack(side="left", padx=6)

        # 진행 로그
        self.log = scrolledtext.ScrolledText(self, height=16, width=62, state="disabled", font=("Courier", 11))
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

    def _countdown(self, seconds: int):
        for i in range(seconds, 0, -1):
            if self._stop_flag.is_set():
                break
            self.timer_label.config(text=f"로그인 대기: {i}초")
            self.update_idletasks()
            threading.Event().wait(1)
        self.timer_label.config(text="")

    def _run(self):
        try:
            self._log("브라우저를 열고 있습니다...")
            page = browser.launch()
            page.goto("https://nid.naver.com/nidlogin.login", wait_until="domcontentloaded")
            self._log(f"네이버 로그인 페이지가 열렸습니다. {LOGIN_WAIT_SECONDS}초 안에 로그인하세요.")
            self._countdown(LOGIN_WAIT_SECONDS)

            if self._stop_flag.is_set():
                return

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

                self._log("  ↳ Gemma 4로 댓글 생성 중...")
                try:
                    comment = ai.generate_comment(title or post["title"], content, model=self._ollama_model)
                except Exception as e:
                    self._log(f"  ↳ AI 오류: {e}")
                    continue

                self._log(f"  ↳ 댓글: {comment[:80]}{'...' if len(comment) > 80 else ''}")
                success = naver.post_comment(page, url, comment)
                self._log(f"  ↳ {'완료' if success else '댓글 입력란을 찾지 못했습니다'}")
                browser.human_delay(1.5, 3.0)

            self._log("=== 모든 작업 완료 ===")
        except Exception as e:
            self._log(f"오류 발생: {e}")
        finally:
            browser.close()
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
