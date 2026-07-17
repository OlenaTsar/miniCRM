import pytest

from .factories import UserFactory
from auth_app.permissions import IsAdmin, IsManager, IsSalesRep, IsEmployee


@pytest.mark.django_db
class TestIsAdminPermission:
    def test_admin_has_permission(self, rf):
        user = UserFactory(role="admin")
        request = rf.get("/")
        request.user = user
        assert IsAdmin().has_permission(request, None) is True

    def test_manager_has_no_permission(self, rf):
        user = UserFactory(role="manager")
        request = rf.get("/")
        request.user = user
        assert IsAdmin().has_permission(request, None) is False

    def test_unauthenticated_has_no_permission(self, rf):
        from django.contrib.auth.models import AnonymousUser
        request = rf.get("/")
        request.user = AnonymousUser()
        assert IsAdmin().has_permission(request, None) is False


@pytest.mark.django_db
class TestIsManagerPermission:
    def test_admin_has_permission(self, rf):
        user = UserFactory(role="admin")
        request = rf.get("/")
        request.user = user
        assert IsManager().has_permission(request, None) is True

    def test_manager_has_permission(self, rf):
        user = UserFactory(role="manager")
        request = rf.get("/")
        request.user = user
        assert IsManager().has_permission(request, None) is True

    def test_sales_rep_has_no_permission(self, rf):
        user = UserFactory(role="sales_rep")
        request = rf.get("/")
        request.user = user
        assert IsManager().has_permission(request, None) is False


@pytest.mark.django_db
class TestIsSalesRepPermission:
    def test_sales_rep_has_permission(self, rf):
        user = UserFactory(role="sales_rep")
        request = rf.get("/")
        request.user = user
        assert IsSalesRep().has_permission(request, None) is True

    def test_manager_has_permission(self, rf):
        user = UserFactory(role="manager")
        request = rf.get("/")
        request.user = user
        assert IsSalesRep().has_permission(request, None) is True

    def test_employee_has_no_permission(self, rf):
        user = UserFactory(role="employee")
        request = rf.get("/")
        request.user = user
        assert IsSalesRep().has_permission(request, None) is False


@pytest.mark.django_db
class TestIsEmployeePermission:
    def test_employee_has_permission(self, rf):
        user = UserFactory(role="employee")
        request = rf.get("/")
        request.user = user
        assert IsEmployee().has_permission(request, None) is True

    def test_admin_has_permission(self, rf):
        user = UserFactory(role="admin")
        request = rf.get("/")
        request.user = user
        assert IsEmployee().has_permission(request, None) is True

    def test_unauthenticated_has_no_permission(self, rf):
        from django.contrib.auth.models import AnonymousUser
        request = rf.get("/")
        request.user = AnonymousUser()
        assert IsEmployee().has_permission(request, None) is False
