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
    try:
        # Create requests session with 10-second timeout
        session = requests_lib.Session()
        session.timeout = 10

        # Create Request object with custom session
        request = requests.Request(session=session)

        # Verify token with timeout protection
        idinfo = id_token.verify_oauth2_token(
            token,
            request,
            GOOGLE_CLIENT_ID
        )

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
    max_retries = 3
    retry_delay = 0.5  # Start with 500ms delay

    for attempt in range(max_retries):
        try:
            # Check if user exists
            result = await db.execute(select(User).filter(User.google_id == google_user_data['google_id']))
            user = result.scalar_one_or_none()

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
                # Update user info if changed
                user.name = google_user_data.get('name')
                user.picture = google_user_data.get('picture')
                await db.commit()
                logger.debug("user_updated", user_id=user.id)

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
