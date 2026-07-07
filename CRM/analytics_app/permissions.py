from rest_framework.permissions import BasePermission
from auth_app.models import UserRole


class HasRole(BasePermission):

    allowed_roles = []

    def has_permission(self, request, view):

        return (
            request.user.is_authenticated
            and request.user.role in self.allowed_roles
        )


class IsAdmin(HasRole):

    allowed_roles = [UserRole.ADMIN]


class IsManager(HasRole):

    allowed_roles = [
        UserRole.ADMIN,
        UserRole.MANAGER,
    ]


class IsSalesRep(HasRole):

    allowed_roles = [
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.SALES_REP,
    ]


class IsEmployee(HasRole):

    allowed_roles = [
        UserRole.ADMIN,
        UserRole.MANAGER,
        UserRole.SALES_REP,
        UserRole.EMPLOYEE,
    ]

