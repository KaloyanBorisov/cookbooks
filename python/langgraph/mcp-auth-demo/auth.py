import os
import httpx
from typing import Optional
from dotenv import load_dotenv
from langgraph_sdk import Auth

load_dotenv()

# LangGraph auth handler — registered in langgraph.json under "auth"
auth = Auth()

# Secret key is used for server-side Vault calls (has elevated privileges)
# Publishable key is used for client-facing token validation (safe to expose to users)
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]


async def get_user_github_token(user_id: str) -> Optional[str]:
    """Fetch the user's GitHub PAT from Supabase Vault.

    Secrets are stored under the key "github_pat_{user_id}" so each user
    has their own isolated token. Falls back to the global GITHUB_PAT env
    var for local dev when Vault isn't set up yet.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/vault_read_secret",
                json={"secret_name": f"github_pat_{user_id}"},
                headers={
                    # Secret key required — Vault is not accessible with the publishable key
                    "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
                    "apikey": SUPABASE_SECRET_KEY,
                    "Content-Type": "application/json",
                },
            )
            if response.status_code == 200 and response.json():
                return response.json()
    except Exception:
        pass

    # Fallback: useful for local dev without a Vault setup
    return os.getenv("GITHUB_PAT")


@auth.authenticate
async def get_current_user(authorization: str | None):
    """Validate the incoming Supabase JWT and build the user identity.

    Runs on every request before any graph node executes. The returned dict
    is attached to the LangGraph request config under
    config["configurable"]["langgraph_auth_user"] and can be read by any
    node via get_config().
    """
    if not authorization:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Missing authorization header")

    # Expect "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        assert scheme.lower() == "bearer"
    except Exception:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid authorization header format")

    # Validate the JWT against Supabase Auth — this also decodes the user claims
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={"Authorization": authorization, "apikey": SUPABASE_PUBLISHABLE_KEY},
            )
            if response.status_code != 200:
                raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid token")
            user = response.json()
    except httpx.HTTPError as e:
        raise Auth.exceptions.HTTPException(status_code=401, detail=f"Token validation failed: {e}")

    # Fetch this user's GitHub PAT from Vault so the agent can use it for MCP
    github_token = await get_user_github_token(user["id"])

    return {
        "identity": user["id"],        # used as the owner key for thread scoping below
        "is_authenticated": True,
        "email": user.get("email"),
        "role": user.get("user_metadata", {}).get("role", "user"),
        "github_token": github_token,  # passed to agent.py via request config
    }


@auth.on.threads.create
@auth.on.threads.read
@auth.on.threads.update
@auth.on.threads.delete
@auth.on.threads.search
async def add_owner(ctx: Auth.types.AuthContext, value: dict) -> dict:
    """Enforce per-user thread isolation.

    Automatically tags every thread with the authenticated user's identity
    and restricts all queries to only return that user's threads. Without
    this, any authenticated user could read or modify another user's threads.
    """
    filters = {"owner": ctx.user.identity}
    if value is not None:
        # Tag new/updated resources with the owner so they can be filtered later
        value.setdefault("metadata", {}).update(filters)
    return filters


__all__ = ["auth"]
