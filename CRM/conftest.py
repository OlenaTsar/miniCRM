import pytest
from rest_framework.test import APIClient
from auth_app.tests.factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user():
    return UserFactory(role="admin", is_verified=True, is_active=True)


@pytest.fixture
def manager_user():
    return UserFactory(role="manager", is_verified=True, is_active=True)


@pytest.fixture
def sales_rep_user():
    return UserFactory(role="sales_rep", is_verified=True, is_active=True)


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def manager_client(api_client, manager_user):
    api_client.force_authenticate(user=manager_user)
    return api_client


@pytest.fixture(autouse=True)
def celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
