# 빌드 컨텍스트는 프로젝트 루트여야 한다 (simulator/, amhs/를 backend가 import하므로):
#   docker build -f backend/Dockerfile -t semisense-backend .
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY simulator/ simulator/
COPY amhs/ amhs/
COPY backend/ backend/
COPY models/ models/
COPY data/processed/ data/processed/

# models/, data/processed/에 joblib/csv 아티팩트가 없으면(노트북을 먼저 안 돌린 클론이면)
# ML 의존 엔드포인트는 503을 반환하고 나머지(시뮬레이터, AMHS 등)는 정상 동작한다 — main.py가
# 이미 이 상황을 gracefully 처리하도록 설계돼 있다.

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
