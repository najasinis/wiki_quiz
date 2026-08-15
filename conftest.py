"""
pytest가 `wiki_quiz` 패키지를 찾을 수 있도록 src/ 를 sys.path에 추가한다.

배경: src/wiki_quiz/*.py 내부 모듈들은 서로를 `from wiki_quiz.xxx import ...`
형태(앞에 `src.`가 없는 절대 임포트)로 참조한다. `python -m src.wiki_quiz.main`으로
실행하면 저장소 루트만 sys.path에 올라가고 src/ 자체는 올라가지 않아
`ModuleNotFoundError: No module named 'wiki_quiz'`가 발생한다 (실제 실행해서 재현·확인함).

이 conftest.py와 scripts/run_local.sh / .github/workflows/daily_quiz.yml에 추가한
PYTHONPATH=src 설정이 그 문제를 해결한다.
"""

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
