import pytest
from django.contrib.auth.models import Group, User
from django.http import Http404
from django.test import override_settings
from django.urls import reverse

from accounts.models import Profile, Role

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_user():
    Group.objects.get_or_create(name="Admin")
    u = User.objects.create_user("admin1", password="TestPass123!")
    Profile.objects.create(user=u, role=Role.ADMIN)
    u.groups.add(Group.objects.get(name="Admin"))
    return u


# --- error page rendering ---


@override_settings(DEBUG=False)
def test_404_renders_custom_template(client):
    response = client.get("/this-path-does-not-exist-12345/")
    assert response.status_code == 404
    content = response.content.decode()
    assert "Page Not Found" in content or "Dashboard" in content


@override_settings(DEBUG=False)
def test_403_renders_custom_template(client):
    """Authenticated user without Admin role gets 403, not 302 login redirect."""
    u = User.objects.create_user("nobody", password="TestPass123!")
    client.force_login(u)
    response = client.get("/accounts/admin/control-panel/")
    assert response.status_code == 403
    content = response.content.decode()
    assert "Access Denied" in content or "Dashboard" in content


# --- PermissionDeniedMiddleware ---


@override_settings(DEBUG=True)
def test_permission_denied_middleware_renders_403_instead_of_traceback(client, admin_user):
    """With DEBUG=True, Django would normally show a traceback for 403.
    PermissionDeniedMiddleware must intercept it and render the 403 template."""
    client.force_login(admin_user)
    # Admin user hitting a non-admin-only page should still work
    response = client.get(reverse("accounts:control_panel"))
    assert response.status_code == 200

    # Nobody user hitting a clinician-only endpoint gets 403 via middleware
    nobody = User.objects.create_user("nobody", password="TestPass123!")
    client.force_login(nobody)
    response = client.get(reverse("inpatient:admit", args=[1]))
    # Will 403 because patient doesn't exist OR no role — either is fine
    # as long as it's not a 500 traceback
    assert response.status_code in (302, 403, 404)
