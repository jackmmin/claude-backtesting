#!/bin/bash
# 코드 업데이트 및 서비스 재시작
# 사용법: bash update.sh

set -e

APP_DIR="/home/ubuntu/claude-coin"

echo "=== 코드 업데이트 ==="
cd "$APP_DIR"
git pull

echo "=== 패키지 업데이트 (변경 시에만) ==="
venv/bin/pip install -r requirements.txt --quiet

echo "=== 서비스 재시작 ==="
sudo systemctl restart claude-coin
sudo systemctl status claude-coin --no-pager

echo "=== 완료 ==="
