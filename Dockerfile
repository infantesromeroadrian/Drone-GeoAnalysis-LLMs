FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libfontconfig1 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/.cache/ultralytics && \
    chown -R appuser:appuser /home/appuser/.cache && \
    mkdir -p logs results missions && \
    chown -R appuser:appuser /app

ENV PYTHONPATH=/app

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')" || exit 1

CMD ["python", "src/main.py"]
