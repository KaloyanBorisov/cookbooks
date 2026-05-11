FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 2024

ENTRYPOINT []
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "2024", "--no-browser"]
