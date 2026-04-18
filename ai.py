import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4"
FALLBACK_MODEL = "gemma3"


def check_ollama() -> tuple[bool, str]:
    """Ollama 실행 여부 및 사용 가능한 모델 확인."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code != 200:
            return False, ""
        models = [m["name"].split(":")[0] for m in resp.json().get("models", [])]
        if MODEL_NAME in models:
            return True, MODEL_NAME
        if FALLBACK_MODEL in models:
            return True, FALLBACK_MODEL
        return False, ""
    except Exception:
        return False, ""


def generate_comment(title: str, content: str, model: str = MODEL_NAME) -> str:
    prompt = (
        f"다음 블로그 글을 읽고 진심 어린 댓글을 한국어로 2~3문장으로 작성해줘. "
        f"댓글만 출력하고 다른 말은 하지 마.\n\n"
        f"제목: {title}\n\n"
        f"내용: {content[:600]}"
    )

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["response"].strip()
