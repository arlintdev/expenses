import os
import json
import structlog
import secrets
from typing import Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, status, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import jwt as pyjwt
from sqlalchemy import select

from models import User, AsyncSessionLocal
from mcp_server import list_tools, handle_tool_call, UserContext

logger = structlog.get_logger(__name__)

mcp_app = FastAPI(title="Expenses MCP OAuth Server", version="1.0.0")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8001")

mcp_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pending_auth_requests = {}

async def verify_mcp_token(token: str) -> Optional[dict]:
    """Verify JWT token and return user context."""
    try:
        payload = pyjwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).filter(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                return None

            return {
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
            }
    except pyjwt.ExpiredSignatureError:
        return None
    except Exception as e:
        logger.error("token_verification_error", error=str(e))
        return None

@mcp_app.get("/.well-known/mcp.json")
async def mcp_metadata():
    """MCP server metadata for OAuth discovery."""
    return {
        "name": "Expenses MCP Server",
        "version": "1.0.0",
        "description": "MCP server for expense tracking with OAuth authentication",
        "authorization": {
            "type": "oauth2",
            "authorizationUrl": f"{MCP_SERVER_URL}/oauth/authorize",
            "tokenUrl": f"{MCP_SERVER_URL}/oauth/token",
            "revokeUrl": f"{MCP_SERVER_URL}/oauth/revoke",
            "scopes": ["openid", "email", "profile"],
        }
    }

@mcp_app.get("/oauth/authorize")
async def oauth_authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    state: str = Query(...),
    response_type: str = Query(default="code"),
    code_challenge: str = Query(None),
    code_challenge_method: str = Query(default="S256"),
):
    """OAuth authorization endpoint - redirects to Google OAuth."""

    auth_id = secrets.token_urlsafe(32)
    pending_auth_requests[auth_id] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method,
        "created_at": datetime.utcnow(),
    }

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={MCP_SERVER_URL}/oauth/callback?auth_id={auth_id}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"access_type=offline&"
        f"state={auth_id}"
    )

    logger.info("oauth_authorize", client_id=client_id, auth_id=auth_id)
    return RedirectResponse(url=google_auth_url)

@mcp_app.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    auth_id: str = Query(...),
    state: str = Query(None),
):
    """OAuth callback from Google - exchanges code for token."""

    if auth_id not in pending_auth_requests:
        logger.error("oauth_callback_invalid_auth_id", auth_id=auth_id)
        raise HTTPException(status_code=400, detail="Invalid or expired auth request")

    auth_req = pending_auth_requests[auth_id]

    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": f"{MCP_SERVER_URL}/oauth/callback?auth_id={auth_id}",
                    "grant_type": "authorization_code",
                },
            )

            if token_response.status_code != 200:
                logger.error("google_token_exchange_failed", status=token_response.status_code)
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")

            token_data = token_response.json()
            google_token = token_data.get("id_token")

            from auth import verify_google_token, get_or_create_user, create_access_token

            google_user_data = await verify_google_token(google_token)

            async with AsyncSessionLocal() as db:
                user = await get_or_create_user(db, google_user_data)

            mcp_token = create_access_token(data={"user_id": user.id})

            redirect_uri = auth_req["redirect_uri"]
            callback_state = auth_req["state"]

            del pending_auth_requests[auth_id]

            redirect_url = (
                f"{redirect_uri}?"
                f"code={mcp_token}&"
                f"state={callback_state}"
            )

            logger.info("oauth_callback_success", user_id=user.id)
            return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error("oauth_callback_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication failed")

@mcp_app.post("/oauth/token")
async def oauth_token(
    grant_type: str = Query(...),
    code: str = Query(None),
    redirect_uri: str = Query(None),
    client_id: str = Query(...),
):
    """OAuth token endpoint - exchanges authorization code for access token."""

    if grant_type == "authorization_code":
        if not code:
            raise HTTPException(status_code=400, detail="Missing authorization code")

        return {
            "access_token": code,
            "token_type": "bearer",
            "expires_in": 604800,
        }

    raise HTTPException(status_code=400, detail="Unsupported grant_type")

@mcp_app.post("/oauth/revoke")
async def oauth_revoke(token: str = Query(...)):
    """OAuth token revocation endpoint."""
    logger.info("oauth_revoke")
    return {"success": True}

@mcp_app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        mcp_app,
        host="0.0.0.0",
        port=8001,
        log_level="info",
    )
