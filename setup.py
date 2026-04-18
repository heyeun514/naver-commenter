"""Ollama + Gemma 4 자동 설치 로직."""
import os
import platform
import shutil
import subprocess
import urllib.request
import threading
from pathlib import Path

OLLAMA_MODEL = "gemma4"
OLLAMA_FALLBACK = "gemma3"
OLLAMA_MACOS_URL = "https://ollama.com/download/Ollama-darwin.zip"


def is_ollama_installed() -> bool:
    return shutil.which("ollama") is not None


def is_ollama_running() -> bool:
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def start_ollama_server():
    """백그라운드에서 ollama serve 실행."""
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    import time
    for _ in range(15):
        if is_ollama_running():
            return True
        time.sleep(1)
    return False


def get_installed_models() -> list[str]:
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return [m["name"].split(":")[0] for m in r.json().get("models", [])]
    except Exception:
        return []


def install_ollama_macos(log_fn=print) -> bool:
    """
    macOS에 Ollama를 자동으로 다운로드·설치.
    log_fn: 진행 상황을 전달할 콜백 (GUI log 함수).
    """
    if platform.system() != "Darwin":
        log_fn("macOS 전용 자동 설치입니다.")
        return False

    zip_path = Path.home() / "Downloads" / "Ollama-darwin.zip"
    app_dst = Path("/Applications/Ollama.app")

    log_fn("Ollama 다운로드 중... (수십 MB, 잠시 기다려주세요)")

    def _progress(block_num, block_size, total_size):
        if total_size > 0:
            pct = min(100, block_num * block_size * 100 // total_size)
            log_fn(f"  다운로드: {pct}%", end=True)

    try:
        urllib.request.urlretrieve(OLLAMA_MACOS_URL, zip_path, reporthook=_progress)
    except Exception as e:
        log_fn(f"다운로드 실패: {e}")
        return False

    log_fn("압축 해제 중...")
    try:
        import zipfile
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(Path.home() / "Downloads")
        extracted = Path.home() / "Downloads" / "Ollama.app"
        if extracted.exists():
            if app_dst.exists():
                import shutil as _sh
                _sh.rmtree(app_dst)
            extracted.rename(app_dst)
        zip_path.unlink(missing_ok=True)
    except Exception as e:
        log_fn(f"설치 실패: {e}")
        return False

    # PATH에 ollama CLI 심볼릭 링크 추가
    cli_src = app_dst / "Contents" / "Resources" / "ollama"
    cli_dst = Path("/usr/local/bin/ollama")
    if cli_src.exists() and not cli_dst.exists():
        try:
            os.symlink(cli_src, cli_dst)
        except PermissionError:
            subprocess.run(["sudo", "ln", "-sf", str(cli_src), str(cli_dst)])

    log_fn("Ollama 설치 완료!")
    return True


def pull_model(model: str, log_fn=print) -> bool:
    """ollama pull <model> 실행 후 완료까지 대기."""
    log_fn(f"모델 다운로드 중: {model}  (수 GB, 시간이 걸릴 수 있어요)")
    try:
        proc = subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            line = line.strip()
            if line:
                log_fn(f"  {line}", end=True)
        proc.wait()
        return proc.returncode == 0
    except Exception as e:
        log_fn(f"모델 다운로드 실패: {e}")
        return False


def ensure_ready(log_fn=print) -> tuple[bool, str]:
    """
    Ollama 설치 → 서버 실행 → 모델 확인/다운로드를 순서대로 보장.
    반환: (성공 여부, 사용할 모델명)
    """
    # 1. 설치 확인
    if not is_ollama_installed():
        log_fn("Ollama가 설치되어 있지 않습니다. 자동 설치를 시작합니다...")
        if not install_ollama_macos(log_fn):
            return False, ""

    # 2. 서버 실행 확인
    if not is_ollama_running():
        log_fn("Ollama 서버를 시작하는 중...")
        if not start_ollama_server():
            log_fn("Ollama 서버를 시작하지 못했습니다.")
            return False, ""
        log_fn("Ollama 서버 시작 완료.")

    # 3. 모델 확인
    models = get_installed_models()
    if OLLAMA_MODEL in models:
        return True, OLLAMA_MODEL
    if OLLAMA_FALLBACK in models:
        return True, OLLAMA_FALLBACK

    # 4. 모델 다운로드
    log_fn(f"'{OLLAMA_MODEL}' 모델이 없습니다. 다운로드를 시작합니다...")
    if pull_model(OLLAMA_MODEL, log_fn):
        return True, OLLAMA_MODEL

    log_fn(f"'{OLLAMA_MODEL}' 실패. '{OLLAMA_FALLBACK}'을 시도합니다...")
    if pull_model(OLLAMA_FALLBACK, log_fn):
        return True, OLLAMA_FALLBACK

    return False, ""
