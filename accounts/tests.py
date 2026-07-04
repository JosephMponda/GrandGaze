import pytest
from django.contrib.auth.models import Group, User
from django.test import override_settings
from django.urls import reverse

from accounts.models import Profile, Role

pytestmark = pytest.mark.django_db


@pytest.fixture
def nurse_user():
    Group.objects.get_or_create(name="Nurse")
    u = User.objects.create_user("nurse1", password="TestPass123!")
    Profile.objects.create(user=u, role=Role.NURSE)
    u.groups.add(Group.objects.get(name="Nurse"))
    return u


# --- happy path ---


def test_correct_credentials_log_in(client, nurse_user):
    response = client.post(reverse("accounts:login"), {"username": "nurse1", "password": "TestPass123!"})
    assert response.status_code == 302


# --- permission-denied / security path ---


@override_settings(AXES_ENABLED=True, AXES_FAILURE_LIMIT=5, AXES_COOLOFF_TIME=0.25)
def test_sixth_failed_login_locks_account_even_with_correct_password(client, nurse_user):
    """Regression test for AGENTS.md §7: 5 failed logins -> 15 min lock.

    This threshold silently drifted from 5 to 10 in a prior commit (paired
    with a since-reverted demo-login-buttons feature) with nothing to catch
    it, because this app had no tests at all. Don't remove this test, and if
    AXES_FAILURE_LIMIT ever needs to change, change it here too.
    """
    for _ in range(4):
        response = client.post(reverse("accounts:login"), {"username": "nurse1", "password": "wrong"})
        assert response.status_code == 200  # normal re-rendered login form with error

    # 5th failure reaches AXES_FAILURE_LIMIT and locks out immediately.
    response = client.post(reverse("accounts:login"), {"username": "nurse1", "password": "wrong"})
    assert response.status_code == 429

    # Still locked on the next attempt, even with the *correct* password.
    response = client.post(reverse("accounts:login"), {"username": "nurse1", "password": "TestPass123!"})
    assert response.status_code == 429


def test_wrong_password_does_not_log_in(client, nurse_user):
    response = client.post(reverse("accounts:login"), {"username": "nurse1", "password": "wrong"})
    assert response.status_code == 200
    assert not response.wsgi_request.user.is_authenticated


# --- logout / redirect behaviour (regression tests) ---


def test_logout_get_redirects_instead_of_405(client, nurse_user):
    """GET /logout/ must redirect (Django 5.x LogoutView dropped get())."""
    client.force_login(nurse_user)
    response = client.get(reverse("accounts:logout"))
    assert response.status_code == 302
    assert "/accounts/login/" in response.headers["Location"]


def test_logged_in_user_redirected_from_login_page(client, nurse_user):
    """redirect_authenticated_user=True sends logged-in users to dashboard."""
    client.force_login(nurse_user)
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 302
    assert reverse("accounts:dashboard") in response.headers["Location"]


def test_control_panel_renders_without_crash(client, nurse_user):
    """Control panel must not throw NoReverseMatch (regression for ward_dashboard)."""
    Group.objects.get_or_create(name="Admin")
    nurse_user.groups.add(Group.objects.get(name="Admin"))
    client.force_login(nurse_user)
    response = client.get(reverse("accounts:control_panel"))
    assert response.status_code == 200
    assert "Control Panel" in response.content.decode()


# --- validation-failure path ---


def test_login_requires_username_and_password(client):
    response = client.post(reverse("accounts:login"), {"username": "", "password": ""})
    assert response.status_code == 200
    assert response.context["form"].errors
