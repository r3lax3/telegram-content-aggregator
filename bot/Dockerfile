# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1


RUN apt-get update
RUN apt-get install -y entr

RUN rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir uv
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

CMD ["sh", "-c", "find . -name '*.py' | entr -r -n python main.py"]
