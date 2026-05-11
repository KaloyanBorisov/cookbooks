import os
import httpx
from typing import Optional
from dotenv import load_dotenv
from langgraph_sdk import Auth

load_dotenv()

auth = Auth()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]
SUPABASE_PUBLISHABLE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]


async def get_user_github_token(user_id: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/vault_read_secret",
                json={"secret_name": f"github_pat_{user_id}"},
                headers={
                    "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
                    "apikey": SUPABASE_SECRET_KEY,
                    "Content-Type": "application/json",
                },
            )
            if response.status_code == 200 and response.json():
                return response.json()
    except Exception:
        pass

    return os.getenv("GITHUB_PAT")


@auth.authenticate
async def get_current_user(authorization: str | None):
    if not authorization:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Missing authorization header")

    try:
        scheme, token = authorization.split()
        assert scheme.lower() == "bearer"
    except Exception:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Invalid authorization header format")

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

    github_token = await get_user_github_token(user["id"])

    return {
        "identity": user["id"],
        "is_authenticated": True,
        "email": user.get("email"),
        "role": user.get("user_metadata", {}).get("role", "user"),
        "github_token": github_token,
    }


@auth.on.threads.create
@auth.on.threads.read
@auth.on.threads.update
@auth.on.threads.delete
@auth.on.threads.search
async def add_owner(ctx: Auth.types.AuthContext, value: dict) -> dict:
    filters = {"owner": ctx.user.identity}
    if value is not None:
        value.setdefault("metadata", {}).update(filters)
    return filters


__all__ = ["auth"]
