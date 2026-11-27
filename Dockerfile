FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AGENTGIS_DB_PATH=/data/agentgis.db

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Hugging Face Spaces 容器以非 root 运行
RUN mkdir -p /data && useradd -m -u 1000 appuser && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
