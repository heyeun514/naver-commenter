#!/bin/bash
set -e

echo "=== 의존성 설치 ==="
pip install -r requirements.txt
playwright install chromium

echo "=== PyInstaller로 .app 빌드 ==="
pyinstaller \
  --windowed \
  --name "네이버댓글봇" \
  --osx-bundle-identifier "com.local.naver-commenter" \
  --add-data "$(python -c 'import playwright; import os; print(os.path.dirname(playwright.__file__))'):playwright" \
  main.py

echo ""
echo "빌드 완료: dist/네이버댓글봇.app"
echo ""
echo "친구에게 전달 시 안내사항:"
echo "  1. https://ollama.com/download 에서 Ollama 설치"
echo "  2. 터미널에서: ollama pull gemma4"
echo "  3. 앱 실행"
