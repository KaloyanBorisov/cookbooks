FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME ["/app"]

EXPOSE 8123

HEALTHCHECK CMD curl --fail http://localhost:8123/ok || exit 1

ENTRYPOINT ["langgraph", "dev", "--host", "0.0.0.0", "--port", "8123"]
