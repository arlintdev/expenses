from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from google.oauth2 import id_token
from google.auth.transport import requests
import requests as requests_lib  # For custom session with timeout
import structlog
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
import asyncio
from models import User, get_db

# Get structured logger for auth module
logger = structlog.get_logger(__name__)

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 168  # Maximum session time: 7 days (168 hours)

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def verify_google_token(token: str) -> dict:
    """
    Verify Google OAuth token with timeout protection.

    Args:
        token: Google ID token to verify

    Returns:
        dict: User information from token

    Raises:
        HTTPException: If token is invalid, expired, or verification times out
    """
    import time
    start_time = time.time()

    try:
        # Create requests session with 10-second timeout
        session = requests_lib.Session()
        session.timeout = 10

        # Create Request object with custom session
        request = requests.Request(session=session)

        # Verify token with timeout protection
        logger.debug("google_token_verification_start")
        idinfo = id_token.verify_oauth2_token(
            token,
            request,
            GOOGLE_CLIENT_ID
        )
        verification_time = (time.time() - start_time) * 1000
        logger.info("google_token_verification_complete", duration_ms=round(verification_time, 2))

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.warning(
                "invalid_token_issuer",
                issuer=idinfo['iss']
            )
            raise ValueError('Wrong issuer.')

        # Log successful verification (without sensitive data)
        logger.info(
            "google_token_verified",
            email_domain=idinfo['email'].split('@')[1] if '@' in idinfo['email'] else "unknown"
        )

        return {
            'google_id': idinfo['sub'],
            'email': idinfo['email'],
            'name': idinfo.get('name'),
            'picture': idinfo.get('picture')
        }

    except requests_lib.exceptions.Timeout as e:
        logger.error(
            "google_token_verification_timeout",
            timeout_seconds=10
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Google authentication service is not responding. Please try again."
        )
    except ValueError as e:
        logger.warning(
            "google_token_validation_failed",
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        logger.error(
            "google_token_verification_error",
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication verification failed. Please try logging in again."
        )

async def get_or_create_user(db: AsyncSession, google_user_data: dict) -> User:
    """
    Get or create user with retry logic for database locks.

    Args:
        db: Database session
        google_user_data: User data from Google OAuth

    Returns:
        User: Created or existing user

    Raises:
        HTTPException: If database operations fail after retries
    """
    import time
    start_time = time.time()

    max_retries = 3
    retry_delay = 0.5  # Start with 500ms delay

    for attempt in range(max_retries):
        try:
            # Check if user exists - explicitly load all columns
            db_lookup_start = time.time()
            result = await db.execute(
                select(User)
                .filter(User.google_id == google_user_data['google_id'])
            )
            user = result.scalar_one_or_none()
            db_lookup_time = (time.time() - db_lookup_start) * 1000
            logger.debug("user_lookup_complete", duration_ms=round(db_lookup_time, 2))

            if not user:
                # Create new user
                user = User(
                    google_id=google_user_data['google_id'],
                    email=google_user_data['email'],
                    name=google_user_data.get('name'),
                    picture=google_user_data.get('picture')
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
                logger.info("user_created", user_id=user.id)
            else:
                # Update user info only if actually changed (avoid unnecessary writes)
                needs_update = False
                if user.name != google_user_data.get('name'):
                    user.name = google_user_data.get('name')
                    needs_update = True
                if user.picture != google_user_data.get('picture'):
                    user.picture = google_user_data.get('picture')
                    needs_update = True

                if needs_update:
                    await db.commit()
                    await db.refresh(user)
                    logger.debug("user_updated", user_id=user.id)
                else:
                    # Only refresh if we didn't just update (avoid redundant query)
                    await db.refresh(user)
                    logger.debug("user_unchanged", user_id=user.id)

            total_time = (time.time() - start_time) * 1000
            logger.info("get_or_create_user_complete", duration_ms=round(total_time, 2), is_new=not user)
            return user

        except OperationalError as e:
            # Database is locked
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                logger.warning(
                    "database_locked_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay_ms=retry_delay * 1000
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                await db.rollback()  # Rollback the failed transaction
                continue
            else:
                logger.error(
                    "database_operation_failed",
                    error=str(e),
                    attempt=attempt + 1
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database is temporarily unavailable. Please try again in a moment."
                )
        except Exception as e:
            logger.error(
                "get_or_create_user_error",
                error=str(e),
                error_type=type(e).__name__
            )
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve user account."
            )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = verify_token(token)
    user_id: int = payload.get("user_id")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency that ensures the current user is an admin.
    Raises 403 Forbidden if user is not an admin.

    Usage:
        @app.get("/api/admin/stats")
        async def admin_stats(admin: User = Depends(get_admin_user)):
            # Only admins can access this endpoint
            pass
    """
    if not current_user.is_admin:
        logger.warning(
            "unauthorized_admin_access",
            user_id=current_user.id,
            email=current_user.email
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. You do not have permission to access this resource."
        )

    logger.info("admin_access_granted", user_id=current_user.id)
    return current_user
