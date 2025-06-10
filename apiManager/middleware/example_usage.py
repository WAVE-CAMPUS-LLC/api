"""
Example usage of the admin access middleware for FastAPI routes.

This file demonstrates different ways to apply role-based access control
to your FastAPI routes using Django groups and permissions.
"""

from fastapi import APIRouter, Depends
from authenticationApp.models import CustomUser
from apiManager.middleware.adminAccess import (
    require_admin_role,
    require_super_admin_role,
    require_member_role,
    require_roles,
    require_permissions,
    get_user_with_roles,
)

router = APIRouter()


# Example 1: Using predefined role dependencies
@router.get("/admin-only")
async def admin_only_endpoint(current_user: CustomUser = Depends(require_admin_role)):
    """
    This endpoint requires Admin or Super Admin role.
    The current_user parameter will contain the authenticated user object.
    """
    return {
        "message": "Welcome to admin area!",
        "user": current_user.username,
        "user_id": current_user.id,
    }


@router.get("/super-admin-only")
async def super_admin_only_endpoint(
    current_user: CustomUser = Depends(require_super_admin_role),
):
    """
    This endpoint requires Super Admin role only.
    """
    return {"message": "Welcome to super admin area!", "user": current_user.username}


@router.get("/member-area")
async def member_area_endpoint(current_user: CustomUser = Depends(require_member_role)):
    """
    This endpoint requires Member role or higher (Member, Admin, Super Admin).
    """
    return {"message": "Welcome to member area!", "user": current_user.username}


# Example 2: Using custom role requirements
@router.get("/event-manager-only")
async def event_manager_endpoint(
    current_user: CustomUser = Depends(require_roles(["Event Manager"])),
):
    """
    This endpoint requires Event Manager role specifically.
    """
    return {"message": "Welcome to event management!", "user": current_user.username}


@router.get("/multiple-roles")
async def multiple_roles_endpoint(
    current_user: CustomUser = Depends(
        require_roles(["Admin", "Event Manager", "Support Staff"])
    )
):
    """
    This endpoint allows multiple specific roles.
    User must have at least one of: Admin, Event Manager, or Support Staff.
    """
    return {
        "message": "Welcome! You have one of the required roles.",
        "user": current_user.username,
    }


# Example 3: Using permission-based access
@router.get("/view-users-permission")
async def view_users_permission_endpoint(
    current_user: CustomUser = Depends(require_permissions(["view_users"])),
):
    """
    This endpoint requires the 'view_users' permission.
    """
    return {
        "message": "You have permission to view users!",
        "user": current_user.username,
    }


@router.get("/manage-events-permission")
async def manage_events_permission_endpoint(
    current_user: CustomUser = Depends(
        require_permissions(["manage_all_events", "create_event"])
    )
):
    """
    This endpoint requires either 'manage_all_events' OR 'create_event' permission.
    """
    return {
        "message": "You have event management permissions!",
        "user": current_user.username,
    }


# Example 4: Getting user with roles for manual checking
@router.get("/custom-logic")
async def custom_logic_endpoint(
    current_user: CustomUser = Depends(get_user_with_roles),
):
    """
    This endpoint gets the authenticated user and allows for custom role logic.
    """
    from channels.db import database_sync_to_async

    # Get user's groups
    user_groups = await sync_to_async(list)(
        current_user.groups.values_list("name", flat=True)
    )

    # Custom logic based on roles
    if "Super Admin" in user_groups:
        access_level = "full"
    elif "Admin" in user_groups:
        access_level = "limited"
    elif "Member" in user_groups:
        access_level = "basic"
    else:
        access_level = "none"

    return {
        "message": f"Welcome! Your access level is: {access_level}",
        "user": current_user.username,
        "roles": user_groups,
        "access_level": access_level,
    }


# Example 5: Combining with other dependencies
@router.post("/admin-action/{item_id}")
async def admin_action_endpoint(
    item_id: int, action: str, current_user: CustomUser = Depends(require_admin_role)
):
    """
    This endpoint combines role checking with other parameters.
    """
    return {
        "message": f"Admin {current_user.username} performed '{action}' on item {item_id}",
        "item_id": item_id,
        "action": action,
        "performed_by": current_user.username,
    }


# Example 6: Error handling demonstration
@router.get("/protected-resource")
async def protected_resource_endpoint(
    current_user: CustomUser = Depends(require_super_admin_role),
):
    """
    This endpoint will return:
    - 401 if user is not authenticated
    - 403 if user doesn't have Super Admin role
    - 200 if user has Super Admin role
    """
    return {
        "message": "Access granted to protected resource!",
        "user": current_user.username,
        "resource": "super_secret_data",
    }
