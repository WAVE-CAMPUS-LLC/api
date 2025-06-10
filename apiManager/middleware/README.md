# Admin Access Middleware for FastAPI

This middleware provides role-based access control for FastAPI routes using Django groups and permissions.

## Features

-   **Role-based access control** using Django groups
-   **Permission-based access control** using Django permissions
-   **FastAPI dependency injection** integration
-   **Async/await support** for Django ORM operations
-   **Detailed error messages** for debugging
-   **Flexible configuration** for different access patterns

## Available Django Roles

Based on your Django setup, the following roles are available:

-   `Member` - Basic user access
-   `Admin` - Administrative access
-   `Super Admin` - Full administrative access
-   `Event Manager` - Event management access
-   `Support Staff` - Support ticket access
-   `Suspend` - Suspended users (restricted access)

## Available Django Permissions

Your system includes these permissions:

-   `view_profile_overview` - View profile overview
-   `view_account_settings` - View account settings
-   `view_support_portal` - View support portal
-   `view_users` - View users
-   `manage_users` - Manage users
-   `view_applications` - View applications
-   `manage_applications` - Manage applications
-   `view_departments` - View departments
-   `manage_departments` - Manage departments
-   `view_all_events` - View all events
-   `manage_all_events` - Manage all events
-   `view_support_tickets` - View support tickets
-   `manage_support_tickets` - Manage support tickets
-   `create_event` - Create events
-   `manage_host_event` - Manage host event
-   `view_host_event` - View host event

## Quick Start

### 1. Import the middleware

```python
from apiManager.middleware.adminAccess import (
    require_admin_role,
    require_super_admin_role,
    require_member_role,
    require_roles,
    require_permissions
)
```

### 2. Apply to your routes

```python
from fastapi import APIRouter, Depends
from authenticationApp.models import CustomUser

router = APIRouter()

@router.get("/admin-dashboard")
async def admin_dashboard(current_user: CustomUser = Depends(require_admin_role)):
    return {"message": f"Welcome admin {current_user.username}!"}
```

## Usage Examples

### Predefined Role Dependencies

```python
# Requires Admin or Super Admin role
@router.get("/admin-area")
async def admin_area(current_user: CustomUser = Depends(require_admin_role)):
    return {"message": "Admin area"}

# Requires Super Admin role only
@router.get("/super-admin-area")
async def super_admin_area(current_user: CustomUser = Depends(require_super_admin_role)):
    return {"message": "Super admin area"}

# Requires Member role or higher
@router.get("/member-area")
async def member_area(current_user: CustomUser = Depends(require_member_role)):
    return {"message": "Member area"}
```

### Custom Role Requirements

```python
# Single custom role
@router.get("/event-manager-only")
async def event_manager_only(
    current_user: CustomUser = Depends(require_roles(["Event Manager"]))
):
    return {"message": "Event manager area"}

# Multiple roles (user needs ANY of these)
@router.get("/staff-area")
async def staff_area(
    current_user: CustomUser = Depends(require_roles(["Admin", "Support Staff", "Event Manager"]))
):
    return {"message": "Staff area"}
```

### Permission-Based Access

```python
# Single permission
@router.get("/view-users")
async def view_users(
    current_user: CustomUser = Depends(require_permissions(["view_users"]))
):
    return {"message": "User list"}

# Multiple permissions (user needs ANY of these)
@router.get("/manage-content")
async def manage_content(
    current_user: CustomUser = Depends(require_permissions(["manage_users", "manage_applications"]))
):
    return {"message": "Content management"}
```

### Custom Logic with User Object

```python
from apiManager.middleware.adminAccess import get_user_with_roles

@router.get("/custom-access")
async def custom_access(current_user: CustomUser = Depends(get_user_with_roles)):
    from channels.db import database_sync_to_async

    # Get user's roles
    user_groups = await sync_to_async(list)(current_user.groups.values_list('name', flat=True))

    # Custom logic
    if "Super Admin" in user_groups:
        access_level = "full"
    elif "Admin" in user_groups:
        access_level = "limited"
    else:
        access_level = "basic"

    return {
        "user": current_user.username,
        "roles": user_groups,
        "access_level": access_level
    }
```

## Error Responses

The middleware returns appropriate HTTP status codes:

### 401 Unauthorized

-   User is not authenticated
-   Invalid or expired token
-   Missing authentication header

```json
{
	"detail": "Authentication required"
}
```

### 403 Forbidden

-   User is authenticated but lacks required roles/permissions

```json
{
	"detail": "Access denied. Required roles: Admin, Super Admin. Your roles: Member"
}
```

### 500 Internal Server Error

-   Database connection issues
-   Unexpected errors during role checking

```json
{
	"detail": "Error checking user permissions: [error details]"
}
```

## Integration with Existing Routes

### Before (without middleware)

```python
@router.get("/users")
async def get_users(current_user_id: str = Depends(get_current_user)):
    # Manual role checking
    user = await sync_to_async(get_object_or_404)(CustomUser, id=current_user_id)
    if not user.groups.filter(name__in=["Admin", "Super Admin"]).exists():
        raise HTTPException(status_code=403, detail="Access denied")

    # Route logic here
    return {"users": []}
```

### After (with middleware)

```python
@router.get("/users")
async def get_users(current_user: CustomUser = Depends(require_admin_role)):
    # Route logic here - user is already validated and loaded
    return {"users": []}
```

## Best Practices

1. **Use specific role dependencies** when possible:

    ```python
    # Good
    current_user: CustomUser = Depends(require_admin_role)

    # Less specific
    current_user: CustomUser = Depends(require_roles(["Admin", "Super Admin"]))
    ```

2. **Combine with other dependencies**:

    ```python
    @router.post("/users/{user_id}/update")
    async def update_user(
        user_id: int,
        user_data: UserUpdateRequest,
        current_user: CustomUser = Depends(require_super_admin_role)
    ):
        # Implementation
    ```

3. **Use permission-based access for fine-grained control**:

    ```python
    # Better for specific actions
    current_user: CustomUser = Depends(require_permissions(["manage_users"]))

    # Better for general areas
    current_user: CustomUser = Depends(require_admin_role)
    ```

4. **Handle the user object efficiently**:
    ```python
    @router.get("/dashboard")
    async def dashboard(current_user: CustomUser = Depends(require_admin_role)):
        # User is already loaded with groups, no need to fetch again
        user_groups = await sync_to_async(list)(current_user.groups.values_list('name', flat=True))
        return {"user": current_user.username, "roles": user_groups}
    ```

## Testing

To test your protected routes:

1. **Ensure user has required roles** in Django admin or through code
2. **Use valid JWT token** in Authorization header: `Bearer <token>`
3. **Check error responses** for proper status codes

Example test setup:

```python
# Create test user with admin role
user = CustomUser.objects.create_user(email="admin@test.com", password="test123")
admin_group = Group.objects.get(name="Admin")
user.groups.add(admin_group)

# Generate token and test
headers = {"Authorization": f"Bearer {jwt_token}"}
response = client.get("/admin-dashboard", headers=headers)
assert response.status_code == 200
```

## Troubleshooting

### Common Issues

1. **"Authentication required" error**:

    - Check if JWT token is valid and not expired
    - Ensure Authorization header format: `Bearer <token>`

2. **"Access denied" error**:

    - Verify user has the required role in Django admin
    - Check role name spelling (case-sensitive)

3. **"Error checking user permissions"**:
    - Check database connection
    - Verify Django models are properly configured

### Debug Tips

1. **Enable logging** to see detailed error messages
2. **Check user roles** in Django admin panel
3. **Verify JWT token** payload contains correct user ID
4. **Test with different user roles** to ensure middleware works correctly
