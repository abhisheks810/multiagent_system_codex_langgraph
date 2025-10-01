FROM python:3.11-slim
WORKDIR /app

# Git (future), tzdata for timezone support
RUN apt-get update && apt-get install -y --no-install-recommends git tzdata && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV REPO_PATH=/workspace/repo
RUN mkdir -p /workspace/repo
VOLUME ["/workspace/repo"]

CMD ["python", "-m", "app.run"]
