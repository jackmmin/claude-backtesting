#!/bin/bash
# Oracle Cloud Ubuntu 서버 최초 1회 실행
# 사용법: bash setup.sh

set -e

APP_DIR="/home/ubuntu/claude-coin"
REPO_URL="https://github.com/<YOUR_GITHUB_USERNAME>/claude-coin.git"  # ← 본인 레포로 변경

echo "=== 1. 시스템 패키지 업데이트 ==="
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

echo "=== 2. 코드 클론 ==="
if [ -d "$APP_DIR" ]; then
    echo "이미 존재하는 디렉토리. git pull로 업데이트합니다."
    cd "$APP_DIR" && git pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

echo "=== 3. Python 가상환경 및 패키지 설치 ==="
cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

echo "=== 4. upbit_keys 파일 생성 ==="
if [ ! -f "$APP_DIR/upbit_keys" ]; then
    echo "upbit_keys 파일이 없습니다. 직접 생성합니다."
    cat > "$APP_DIR/upbit_keys" << 'KEYEOF'
# 업비트 API 키 설정

[balance]
access_key = YOUR_BALANCE_ACCESS_KEY
secret_key = YOUR_BALANCE_SECRET_KEY

[order_query]
access_key = YOUR_ORDER_QUERY_ACCESS_KEY
secret_key = YOUR_ORDER_QUERY_SECRET_KEY

[order]
access_key = YOUR_ORDER_ACCESS_KEY
secret_key = YOUR_ORDER_SECRET_KEY
KEYEOF
    echo ">>> $APP_DIR/upbit_keys 파일을 열어 API 키를 입력하세요: nano $APP_DIR/upbit_keys"
else
    echo "upbit_keys 파일이 이미 존재합니다."
fi

echo "=== 5. systemd 서비스 등록 ==="
sudo cp "$APP_DIR/deploy/claude-coin.service" /etc/systemd/system/claude-coin.service
sudo systemctl daemon-reload
sudo systemctl enable claude-coin

echo ""
echo "=== 설치 완료 ==="
echo "API 키 입력 후 아래 명령으로 서비스를 시작하세요:"
echo "  sudo systemctl start claude-coin"
echo "  sudo systemctl status claude-coin"
echo "  sudo journalctl -u claude-coin -f   # 실시간 로그 확인"
