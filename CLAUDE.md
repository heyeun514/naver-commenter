# 네이버 블로그 이웃 자동 댓글봇

## 프로젝트 개요
네이버 블로그 이웃들의 최신 글을 순회하며 Gemma 4 로컬 모델(Ollama)로 글을 분석하고 맞춤 댓글을 자동 작성하는 Mac 데스크탑 앱.

## 핵심 요구사항
- **로컬 AI**: Ollama + Gemma 4 (또는 Gemma 3 fallback) — 글 분석과 댓글 생성을 모두 로컬에서 처리
- **자동 환경 설정**: 앱 첫 실행 시 Ollama 미설치 → 자동 다운로드/설치, 모델 미설치 → 자동 pull
- **수동 로그인**: 네이버 로그인은 30초 타이머 내에 사용자가 직접 입력 (자동화 없음)
- **Mac 앱 패키징**: PyInstaller로 `.app` 빌드, M1 Mac 포함 배포 가능
- **광범위 배포 목표**: 친구 및 불특정 다수에게 배포 가능한 완전 자립형(self-contained) 앱

## 파일 구조
```
naver-commenter/
├── main.py       — Tkinter GUI, 앱 진입점
├── setup.py      — Ollama/모델 자동 설치 로직
├── browser.py    — Playwright 브라우저 제어 (launch/close/delay)
├── naver.py      — 이웃 피드 크롤링, 본문 추출, 댓글 입력
├── ai.py         — Ollama REST API 연동 (댓글 생성)
├── requirements.txt
└── build.sh      — PyInstaller .app 패키징 스크립트
```

## 기술 스택
- Python 3.11+
- Playwright (브라우저 자동화, Chromium 번들)
- Ollama REST API (`http://localhost:11434`)
- Tkinter (GUI)
- PyInstaller (Mac .app 패키징)

## 개발 실행
```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

## 빌드 (.app)
```bash
./build.sh
# → dist/네이버댓글봇.app
```

## 배포 시 사용자 요구사항
- Ollama 설치 불필요 — 앱이 자동 설치
- Gemma 4 모델 다운로드 불필요 — 앱이 자동 pull
- macOS 지원 (M1/M2/Intel)

## 주요 동작 흐름
1. 앱 실행 → Ollama 설치/서버 기동/모델 확인 자동 수행
2. 시작 버튼 → 브라우저 열림 → 30초 로그인 대기
3. 로그인 완료 → 이웃 피드 크롤링 (최대 N명, 기본 20)
4. 각 글 본문 추출 → Gemma 4로 댓글 생성 → 댓글 자동 입력
5. 글 간 1~3초 랜덤 딜레이 (봇 감지 방지)

## 주의사항
- 네이버 HTML 구조 변경 시 `naver.py`의 CSS 셀렉터 수정 필요
- 네이버 정책상 자동 댓글은 계정 제재 위험 있음 — 앱 내 고지 필요
- Playwright Chromium 번들 포함으로 build.sh의 `--add-data` 경로 주의
