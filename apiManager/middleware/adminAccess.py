from functools import wraps
from fastapi import HTTPException, Depends
from typing import List, Optional, Callable, Any
from asgiref.sync import sync_to_async
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404

from authenticationApp.models import CustomUser
from apiManager.dependencies import get_current_user


async def check_user_roles(user_id: str, required_roles: List[str]) -> CustomUser:
    """
    Check if user has any of the required roles.

    Args:
        user_id: The user ID to check
        required_roles: List of role names (Django group names) that are allowed access

    Returns:
        CustomUser instance if user has required roles

    Raises:
        HTTPException: If user doesn't have required roles or doesn't exist
    """
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        user = await sync_to_async(get_object_or_404)(CustomUser, id=user_id)
        user_groups = await sync_to_async(list)(
            user.groups.values_list("name", flat=True)
        )

        # Check if user has any of the required roles
        has_required_role = any(role in user_groups for role in required_roles)

        if not has_required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}. Your roles: {', '.join(user_groups)}",
            )

        return user

    except CustomUser.DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid user")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking user permissions: {str(e)}"
        )


async def check_user_permissions(
    user_id: str, required_permissions: List[str]
) -> CustomUser:
    """
    Check if user has any of the required permissions.

    Args:
        user_id: The user ID to check
        required_permissions: List of permission codenames that are allowed access

    Returns:
        CustomUser instance if user has required permissions

    Raises:
        HTTPException: If user doesn't have required permissions or doesn't exist
    """
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        user = await sync_to_async(get_object_or_404)(CustomUser, id=user_id)

        # Check if user has any of the required permissions
        has_permission = False
        for permission in required_permissions:
            if await sync_to_async(user.has_perm)(permission):
                has_permission = True
                break

        if not has_permission:
            user_permissions = await sync_to_async(list)(
                user.user_permissions.values_list("codename", flat=True)
            )
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required permissions: {', '.join(required_permissions)}. Your permissions: {', '.join(user_permissions)}",
            )

        return user

    except CustomUser.DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid user")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking user permissions: {str(e)}"
        )


# Dependency functions for FastAPI
async def require_admin_role(
    current_user_id: str = Depends(get_current_user),
) -> CustomUser:
    """FastAPI dependency that requires Admin or Super Admin role."""
    return await check_user_roles(current_user_id, ["Admin", "Super Admin"])


async def require_super_admin_role(
    current_user_id: str = Depends(get_current_user),
) -> CustomUser:
    """FastAPI dependency that requires Super Admin role."""
    return await check_user_roles(current_user_id, ["Super Admin"])


async def require_member_role(
    current_user_id: str = Depends(get_current_user),
) -> CustomUser:
    """FastAPI dependency that requires Member role or higher."""
    return await check_user_roles(current_user_id, ["Member", "Admin", "Super Admin"])


def require_roles(required_roles: List[str]):
    """
    Create a FastAPI dependency that checks for specific roles.

    Args:
        required_roles: List of role names (Django group names) that are allowed access

    Returns:
        FastAPI dependency function
    """

    async def dependency(
        current_user_id: str = Depends(get_current_user),
    ) -> CustomUser:
        return await check_user_roles(current_user_id, required_roles)

    return dependency


def require_permissions(required_permissions: List[str]):
    """
    Create a FastAPI dependency that checks for specific permissions.

    Args:
        required_permissions: List of permission codenames that are allowed access

    Returns:
        FastAPI dependency function
    """

    async def dependency(
        current_user_id: str = Depends(get_current_user),
    ) -> CustomUser:
        return await check_user_permissions(current_user_id, required_permissions)

    return dependency


async def get_user_with_roles(
    current_user_id: str = Depends(get_current_user),
) -> CustomUser:
    """
    Dependency that returns the authenticated user with their roles loaded.

    Args:
        current_user_id: User ID from the authentication dependency

    Returns:
        CustomUser instance with roles loaded

    Raises:
        HTTPException: If user is not found or not authenticated
    """
    if current_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        user = await sync_to_async(get_object_or_404)(CustomUser, id=current_user_id)
        # Prefetch groups for efficiency
        await sync_to_async(user.groups.prefetch_related)()
        return user
    except CustomUser.DoesNotExist:
        raise HTTPException(status_code=401, detail="Invalid user")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading user: {str(e)}")


# Decorator versions (for backward compatibility)
def admin_required(func: Callable) -> Callable:
    """
    Decorator for routes that require Admin or Super Admin access.
    Note: This is for backward compatibility. Use require_admin_role dependency instead.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract current_user_id from kwargs
        current_user_id = kwargs.get("current_user_id")
        await check_user_roles(current_user_id, ["Admin", "Super Admin"])
        return await func(*args, **kwargs)

    return wrapper


def super_admin_required(func: Callable) -> Callable:
    """
    Decorator for routes that require Super Admin access only.
    Note: This is for backward compatibility. Use require_super_admin_role dependency instead.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract current_user_id from kwargs
        current_user_id = kwargs.get("current_user_id")
        await check_user_roles(current_user_id, ["Super Admin"])
        return await func(*args, **kwargs)

    return wrapper


def member_required(func: Callable) -> Callable:
    """
    Decorator for routes that require at least Member access.
    Note: This is for backward compatibility. Use require_member_role dependency instead.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract current_user_id from kwargs
        current_user_id = kwargs.get("current_user_id")
        await check_user_roles(current_user_id, ["Member", "Admin", "Super Admin"])
        return await func(*args, **kwargs)

    return wrapper
