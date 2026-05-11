# mcp-auth-demo

Per-user MCP authentication with LangGraph — each user's GitHub tools run under their own credentials, stored securely in Supabase Vault.

## Agent Pattern

This is **not RAG**. There is no vector store, no document retrieval, no embeddings.

This is a **ReAct agent** (Reason + Act) — the LLM reasons about what GitHub tool to call, calls it via MCP, gets live results back, reasons again, and repeats until it can answer. All data is real-time from the GitHub API, not pre-indexed documents.

```
RAG:    query → retrieve chunks from vector store → augment prompt → answer
ReAct:  query → reason → call live API → reason over result → call again? → answer
```

## How Authentication Intercepts the Request

Every incoming HTTP request passes through `auth.py` before any graph node runs. LangGraph calls `@auth.authenticate` automatically because `auth.py` is registered as the auth handler in `langgraph.json`.

```
HTTP request
     │
     ▼
@auth.authenticate          ← intercepts here
  validate Supabase JWT
  fetch GitHub PAT from Vault
  attach { github_token, email, ... } to request config
     │
     ▼
get_mcp_tools_node          ← first graph node
  read github_token from config
  open MCP connection with that token  ← GitHub MCP authenticated here
     │
     ▼
agent_node                  ← LLM has tools, never touches auth again
```

The middleware does not authenticate the MCP connection directly — it fetches the user's GitHub PAT and hands it off via the request config. The actual MCP authentication happens in `get_mcp_tools_node` when the `Authorization: Bearer <github_token>` header is sent to the GitHub MCP server.

## How It Works

```
Client → Supabase Auth → LangGraph middleware → Supabase Vault → GitHub MCP → Agent
```

1. Client authenticates with Supabase and gets a JWT
2. JWT is sent as `Authorization: Bearer <token>` to LangGraph
3. Custom auth middleware validates the token and fetches the user's GitHub PAT from Supabase Vault
4. Agent initializes GitHub MCP tools with that user's PAT
5. All GitHub API calls use the individual user's credentials

## Architecture

```
👤 User (Bearer JWT)
       │
       ▼
┌─────────────────── auth.py ───────────────────┐
│  validate JWT  ──►  Supabase Auth             │
│  fetch PAT     ──►  Supabase Vault            │
│  scope threads to owner                       │
└───────────────────────┬───────────────────────┘
                        │ github_token in config
                        ▼
┌─────────────────── agent.py ──────────────────┐
│                                               │
│  [1] get_mcp_tools  ──►  GitHub MCP Server   │
│          │                                    │
│  [2] agent (GPT-4o + tools)  ──►  OpenAI     │
│          │                                    │
│     tool calls?                               │
│     ├── yes ──►  [3] tools  ──►  GitHub MCP  │
│     │                │ loop back              │
│     └── no                                    │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
                  💬 Response
```

## Two Tokens, Two Jobs

This project uses two separate tokens that serve completely different purposes:

```
Supabase JWT  →  proves who you are  →  unlocks your GitHub PAT from Vault
GitHub PAT    →  authorizes MCP      →  agent acts as you on GitHub
```

**Supabase JWT** — issued when you log in to Supabase. Sent as `Authorization: Bearer` on every request to the LangGraph agent. The auth middleware validates it, extracts your `user_id`, and uses it to look up your GitHub PAT in the Vault. It never touches GitHub directly.

**GitHub PAT** — your personal GitHub access token, stored once in Supabase Vault. Retrieved per-request by the auth layer and injected into the MCP connection header. This is what actually authorizes the agent to call GitHub on your behalf — accessing your private repos, issues, PRs, and anything else your PAT permits.

The Supabase JWT identifies you. The GitHub PAT acts as you.

### Generating a Token (dev only)

In production, the Supabase JWT comes from your frontend login flow. Locally, since there is no UI, `generate_supabase_token.py` simulates it by calling `supabase.auth.sign_in_with_password()` directly and printing the resulting JWT so you can paste it into curl or LangGraph Studio.

## Prerequisites

- Docker + Docker Compose
- Supabase project (free tier works)
- GitHub Personal Access Token with Copilot access
- OpenAI API key
- LangSmith API key

## Setup

### 1. Configure Environment

Copy `.env.example` to `.env` and fill in:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=sb_secret_...
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
GITHUB_PAT=ghp_...
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=lsv2_...
```

`SUPABASE_SECRET_KEY` maps to the **Secret key** and `SUPABASE_PUBLISHABLE_KEY` to the **Publishable key** in your Supabase project settings.

### 2. Set Up Supabase Vault

Run this SQL in your Supabase **SQL Editor** to create the required Vault helper functions:

```sql
CREATE EXTENSION IF NOT EXISTS supabase_vault WITH SCHEMA vault;

CREATE OR REPLACE FUNCTION vault_create_secret(secret text, name text default null, description text default null)
RETURNS uuid AS $$
BEGIN
  RETURN vault.create_secret(secret, name, description);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION vault_read_secret(secret_name text)
RETURNS text AS $$
DECLARE result text;
BEGIN
  SELECT decrypted_secret INTO result FROM vault.decrypted_secrets WHERE name = secret_name;
  RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION vault_delete_secret(secret_name text)
RETURNS void AS $$
BEGIN
  DELETE FROM vault.secrets WHERE name = secret_name;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

### 3. Initialize Database and Secrets

```bash
# Create test users and store GitHub PATs in Vault
docker compose --profile setup run --rm setup
```

This creates two test users (`user1@example.com`, `user2@example.com`, password `testpass123`) and stores the `GITHUB_PAT` from your `.env` in Supabase Vault for each.

### 4. Start the Server

```bash
docker compose up -d
```

### 5. Generate a Token

```bash
# Default: user1@example.com
docker compose --profile token run --rm token

# Specific user
docker compose --profile token run --rm token python generate_supabase_token.py user2@example.com
```

Copy the `Authorization: Bearer <token>` output.

### 6. Test in LangGraph Studio

1. Open LangGraph Studio and connect to `http://localhost:2024`
2. Add the header: `Authorization: Bearer <your-token>`
3. Send a GitHub-related message, e.g. _"What are my most recent repositories?"_

## Project Structure

```
mcp-auth-demo/
├── agent.py              # LangGraph graph with MCP tool loading
├── auth.py               # Custom auth middleware (Supabase JWT validation + Vault)
├── setup_database.py     # Creates Supabase test users
├── setup_secrets.py      # Stores GitHub PATs in Supabase Vault
├── generate_supabase_token.py  # Generates test JWT tokens
├── langgraph.json        # LangGraph server config
├── pyproject.toml
├── Dockerfile
└── docker-compose.yml    # Services: api, setup (profile), token (profile)
```

## Troubleshooting

**"Could not find function vault_create_secret"** — Run the SQL setup from Step 2.

**"Invalid login credentials"** — The test users don't exist yet; run the setup profile first.

**"No assistants found" in Studio** — The auth token is missing or invalid. Regenerate it with the token profile.

**MCP tools not loading** — Verify your GitHub PAT has Copilot access and is stored in Vault (check Supabase Dashboard → Vault).
