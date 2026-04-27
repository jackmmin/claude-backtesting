# Oracle Cloud 배포 가이드

로컬 실행 방식은 그대로 유지되며, 아래 절차를 따르면 Oracle Cloud에서 24시간 자동매매를 운영할 수 있습니다.

---

## 로컬 vs 클라우드 차이

| 항목 | 로컬 | 클라우드 |
|------|------|----------|
| 실행 | `python app.py` | systemd 자동 실행 |
| 접속 | `http://localhost:5000` | `http://<서버IP>:5000` |
| 환경변수 | 없음 (기본값) | `DEPLOY_MODE=cloud` |
| API 키 | `upbit_keys` (로컬) | `upbit_keys` (서버에 직접 생성) |

---

## 1단계: Oracle Cloud 계정 및 VM 생성

1. [oracle.com/cloud/free](https://www.oracle.com/cloud/free/) 접속 → 무료 계정 가입
2. **Compute → Instances → Create Instance**
3. 설정:
   - Image: **Ubuntu 22.04**
   - Shape: **VM.Standard.A1.Flex** (ARM, 무료) — OCPU 1, Memory 6GB
   - 네트워크: 기본값 유지
   - SSH 키: 본인 SSH 공개키 등록 (없으면 자동 생성 후 다운로드)
4. 인스턴스 생성 완료 후 **공인 IP 확인**

---

## 2단계: 방화벽(포트 5000) 오픈

### Oracle Cloud Security List
1. **Networking → Virtual Cloud Networks → 해당 VCN → Security Lists**
2. **Ingress Rules → Add Ingress Rule**
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: TCP
   - Destination Port: `5000`

### 서버 내부 방화벽
SSH 접속 후:
```bash
sudo iptables -I INPUT -p tcp --dport 5000 -j ACCEPT
sudo netfilter-persistent save   # Ubuntu에서 재부팅 후에도 유지
```

> 보안상 특정 IP만 허용하고 싶다면 Source CIDR을 본인 IP로 변경하세요.

---

## 3단계: GitHub에 코드 푸시

```bash
# 로컬에서
git push origin main
```

> `upbit_keys`, `trading_state.json`, `trading_config.json`은 `.gitignore`에 포함되어 있어 업로드되지 않습니다.

---

## 4단계: 서버 초기 설치

```bash
# 로컬에서 서버 SSH 접속
ssh ubuntu@<서버IP>

# setup.sh에서 레포 URL 수정 후 실행
# deploy/setup.sh 파일의 REPO_URL을 본인 GitHub 레포 주소로 변경
bash <(curl -s https://raw.githubusercontent.com/<YOUR_USERNAME>/claude-coin/main/deploy/setup.sh)

# 또는 직접 클론 후 실행
git clone https://github.com/<YOUR_USERNAME>/claude-coin.git
bash claude-coin/deploy/setup.sh
```

---

## 5단계: API 키 입력

```bash
nano /home/ubuntu/claude-coin/upbit_keys
```

아래 형식으로 입력:
```ini
[balance]
access_key = 실제키입력
secret_key = 실제키입력

[order_query]
access_key = 실제키입력
secret_key = 실제키입력

[order]
access_key = 실제키입력
secret_key = 실제키입력
```

---

## 6단계: 서비스 시작

```bash
sudo systemctl start claude-coin
sudo systemctl status claude-coin   # 실행 확인
```

브라우저에서 `http://<서버IP>:5000` 접속하여 정상 동작 확인.

---

## 이후 코드 업데이트 방법

로컬에서 수정 → `git push` → 서버에서:
```bash
cd /home/ubuntu/claude-coin
bash deploy/update.sh
```

---

## 유용한 명령어

```bash
# 실시간 로그 확인
sudo journalctl -u claude-coin -f

# 서비스 재시작 / 중지
sudo systemctl restart claude-coin
sudo systemctl stop claude-coin

# 부팅 시 자동시작 해제
sudo systemctl disable claude-coin
```
