"""프로젝트 루트의 `.env`를 가장 먼저 읽어 환경변수로 올린다.

`GEMINI_API_KEY`처럼 로컬에서만 설정하는 값들을 다루므로, `os.environ`을 읽는 다른 모듈
(`database.py`의 `SEMISENSE_DATABASE_URL` 등)보다 먼저 import돼야 한다 — `main.py`가 다른
로컬 모듈을 import하기 전에 이 모듈부터 import하는 이유다. `.env`는 `.gitignore`에 이미
포함돼 있어 커밋되지 않는다.
"""
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
