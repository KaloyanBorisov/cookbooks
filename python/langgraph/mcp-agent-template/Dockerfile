FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml langgraph.json mcp-servers-config.json ./
COPY src/ src/

RUN pip install --no-cache-dir -e ".[dev]"

RUN npm install -g @playwright/mcp@latest firecrawl-mcp && \
    npx playwright install chrome --with-deps

EXPOSE 2024
EXPOSE 2025

CMD ["sh", "-c", "if [ \"$DEBUG\" = \"1\" ]; then python -m debugpy --listen 0.0.0.0:2025 --wait-for-client -m langgraph dev --host 0.0.0.0 --port 2024; else langgraph dev --host 0.0.0.0 --port 2024; fi"]
