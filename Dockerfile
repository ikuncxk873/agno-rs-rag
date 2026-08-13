FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FASTEMBED_CACHE_PATH=/app/cache/fastembed \
    HF_ENDPOINT=https://hf-mirror.com

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 预缓存嵌入模型(约 100MB):补齐 HF 缓存结构,fastembed local_files_only 命中,零联网加载
# (fastembed 0.8.0 每次联网校验,xet 路径不可用会 fallback 重下 90MB)
COPY scripts/precache_embedder.py .
RUN python precache_embedder.py && rm precache_embedder.py

COPY app/ ./app/
COPY static/ ./static/
COPY agent_core.py kb_build.py ./

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
