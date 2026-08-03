#!/usr/bin/env bash
# 로컬 수동 실행 / launchd에서 호출할 스크립트.
# GitHub Actions cron 지연이 문제될 경우 이 스크립트를 launchd plist에 연결해 병행 실행 고려.

set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements.txt
python -m src.notion_quiz.main
