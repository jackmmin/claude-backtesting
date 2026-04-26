"""작업 로그 저장 스크립트
사용법: python log.py "[버그수정|개선|추가] 내용"
"""
import sys
import os
from datetime import datetime, timezone, timedelta

LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "LOG.md")
KST = timezone(timedelta(hours=9))


def main():
    if len(sys.argv) < 2:
        print("사용법: python log.py \"[태그] 내용\"")
        sys.exit(1)

    message = " ".join(sys.argv[1:])
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{now}] {message}\n"

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)

    sys.stdout.buffer.write(f"로그 저장: {entry.strip()}\n".encode("utf-8"))


if __name__ == "__main__":
    main()
