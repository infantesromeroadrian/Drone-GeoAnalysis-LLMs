FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for OpenCV, PyTorch and YOLO 11
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1-mesa-glx \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libfontconfig1 \
    libgomp1 \
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create ultralytics cache directory - model will be downloaded at runtime
RUN mkdir -p /root/.cache/ultralytics

# Create application directory structure (will be mounted from host)
RUN mkdir -p logs results missions

# Set environment variable for path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5000

# Use new refactored main.py instead of old app.py
CMD ["python", "src/main.py"] 