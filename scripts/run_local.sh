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

# src/ 내부 모듈들이 `wiki_quiz.xxx` 절대 임포트를 쓰기 때문에 src/를 PYTHONPATH에 넣어야
# `python -m src.wiki_quiz.main` 실행 시 ModuleNotFoundError가 나지 않는다.
export PYTHONPATH="$PWD/src:${PYTHONPATH:-}"
python -m src.wiki_quiz.main
