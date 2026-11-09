FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CHROMA_PATH=/home/rehearsal/data/chroma PUBLIC_DEPLOYMENT=true PARSER_SANDBOX=required PROVIDER_BUDGET_PATH=/home/rehearsal/data/provider-budget.sqlite3
WORKDIR /app
ENV FEEDBACK_DB_PATH=/home/rehearsal/data/feedback.sqlite3
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libseccomp2 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir --require-hashes -r backend/requirements.lock
COPY backend /app/backend
COPY samples /app/samples
COPY scripts/report_feedback.py /app/scripts/report_feedback.py
RUN useradd --create-home rehearsal
USER rehearsal
EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
