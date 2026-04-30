# ================================================
# 后端 Dockerfile - FastAPI + Python 3.11
# ================================================

ARG PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.11-slim-bookworm
FROM ${PYTHON_IMAGE}

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .

RUN pip install --upgrade pip --progress-bar off -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --progress-bar off --timeout 120 --retries 10 -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 8011

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8011/health', timeout=5)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8011", "--loop", "asyncio", "--http", "h11"]
