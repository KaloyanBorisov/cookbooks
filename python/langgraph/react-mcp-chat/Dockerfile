FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt pyproject.toml langgraph.json ./
COPY src/ src/

RUN pip install --no-cache-dir -e ".[dev]"

RUN npm install -g \
    @modelcontextprotocol/server-brave-search \
    hyperbrowser-mcp \
    todoist-mcp

EXPOSE 2024

CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "2024"]
