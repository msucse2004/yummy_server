FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# 마이그레이션 → admin 사용자 초기화 → 서버 시작
CMD alembic -c alembic.ini upgrade head && python scripts/init_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000
