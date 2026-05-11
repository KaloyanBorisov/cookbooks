FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml langgraph.json ./
COPY agent.py auth.py setup_database.py setup_secrets.py generate_supabase_token.py ./

RUN pip install --no-cache-dir -e "."

EXPOSE 2024
EXPOSE 2025

CMD ["sh", "-c", "if [ \"$DEBUG\" = \"1\" ]; then python -m debugpy --listen 0.0.0.0:2025 --wait-for-client -m langgraph dev --host 0.0.0.0 --port 2024; else langgraph dev --host 0.0.0.0 --port 2024; fi"]
