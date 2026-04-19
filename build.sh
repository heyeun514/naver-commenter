#!/bin/bash
set -e

PYTHON=/opt/homebrew/bin/python3.11

echo "=== 의존성 설치 ==="
$PYTHON -m pip install -r requirements.txt
$PYTHON -m playwright install chromium

echo "=== 경로 확인 ==="
PW_PATH=$($PYTHON -c 'import playwright; import os; print(os.path.dirname(playwright.__file__))')
BROWSER_DIR="$HOME/Library/Caches/ms-playwright"
echo "Playwright: $PW_PATH"
echo "Chromium: $BROWSER_DIR"

echo "=== PyInstaller로 .app 빌드 ==="
rm -rf dist/ build/ *.spec
$PYTHON -m PyInstaller \
  --windowed \
  --name "네이버댓글봇" \
  --osx-bundle-identifier "com.local.naver-commenter" \
  --add-data "${PW_PATH}:playwright" \
  --hidden-import playwright \
  --hidden-import playwright.sync_api \
  --hidden-import requests \
  --collect-all playwright \
  main.py

echo "=== Chromium 브라우저 번들 복사 ==="
DEST="dist/네이버댓글봇.app/Contents/Resources/playwright/driver/package/.local-browsers"
mkdir -p "$DEST"
cp -R "$BROWSER_DIR"/chromium-* "$DEST/"
echo "Chromium 복사 완료"

APP_SIZE=$(du -sh "dist/네이버댓글봇.app" | cut -f1)
echo "앱 크기: $APP_SIZE"

echo "=== zip 압축 중 ==="
cd dist
zip -r -y "../네이버댓글봇.zip" "네이버댓글봇.app"
cd ..
ZIP_SIZE=$(du -sh "네이버댓글봇.zip" | cut -f1)
echo ""
echo "완료: 네이버댓글봇.zip ($ZIP_SIZE)"
echo ""
echo "친구에게 전달 방법:"
echo "  1. '네이버댓글봇.zip'을 Google Drive/네이버 MYBOX에 업로드"
echo "  2. 링크 공유"
echo ""
echo "친구 사용법:"
echo "  1. zip 다운로드 후 압축 해제"
echo "  2. '네이버댓글봇.app' 우클릭 → 열기 (보안 경고 뜨면 '열기' 클릭)"
echo "  3. 첫 실행: Ollama + AI 모델 자동 설치 (수 분 소요)"
echo "  4. '시작' 버튼 → 네이버 로그인 → 자동 댓글"
