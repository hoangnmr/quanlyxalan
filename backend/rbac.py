from typing import List, Optional
from fastapi import HTTPException, status, Depends
from .models import User
from .auth import get_current_user

# Final product roles. There is no tenant-local ADMIN; PORT_STAFF performs all
# tenant/port operations for the reporting units in which the user has membership,
# and PLATFORM_ADMIN carries product-wide platform authority.
ROLE_ENUM = {"CUSTOMER", "PORT_STAFF", "PLATFORM_ADMIN"}

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        # Validate that all specified roles are valid
        for r in allowed_roles:
            if r not in ROLE_ENUM:
                raise ValueError(f"Invalid role configuration: {r}")
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        # Check active status
        if not getattr(user, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản đã bị vô hiệu hóa."
            )

        # Validate user role
        if user.role not in ROLE_ENUM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vai trò không hợp lệ."
            )

        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện hành động này."
            )

        # Check CUSTOMER role has an assigned organization
        if user.role == "CUSTOMER" and user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản chưa được liên kết với tổ chức nào."
            )

        return user

def require_roles(*roles: str):
    return RoleChecker(list(roles))

def verify_organization_ownership(user: User, resource_org_id: Optional[int]) -> None:
    """
    Enforces tenant isolation. For CUSTOMER role, verifies that they belong
    to the same organization as the resource.
    """
    if user.role == "CUSTOMER":
        if user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản chưa được liên kết với tổ chức nào."
            )
        if resource_org_id != user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không được phép truy cập dữ liệu của tổ chức khác."
            )
