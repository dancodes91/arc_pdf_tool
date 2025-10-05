"""
Simple authentication module for API endpoints.

Provides basic authentication utilities for the FastAPI application.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """
    Extract current user from authentication credentials.

    For now, this is a simple implementation that returns a default user.
    In production, this would validate JWT tokens or API keys.
    """
    if credentials is None:
        # For testing and development, allow unauthenticated access
        return "anonymous"

    # In production, validate the token and extract user info
    # For now, just return a mock user ID
    return "authenticated_user"


def require_admin(current_user: str = Depends(get_current_user)) -> str:
    """
    Require admin privileges for the current user.

    Args:
        current_user: Current authenticated user

    Returns:
        User ID if user has admin privileges

    Raises:
        HTTPException: If user is not an admin
    """
    # In production, check user roles/permissions
    # For now, allow all authenticated users to be admins
    if current_user == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for admin operations",
        )

    return current_user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[str]:
    """
    Get current user if authenticated, otherwise None.

    Args:
        credentials: Optional authentication credentials

    Returns:
        User ID if authenticated, None otherwise
    """
    if credentials is None:
        return None

    # In production, validate credentials
    return "authenticated_user"
