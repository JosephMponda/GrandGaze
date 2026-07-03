"""
Single source of truth for role checks. AGENTS.md / Engineer A spec §1:
do not hardcode `request.user.profile.role == "NURSE"` scattered through
views — every app imports has_role() from here instead.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def has_role(user, *role_names: str) -> bool:
    """True if `user` belongs to any of the given Django Group names."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=role_names).exists()


def role_required(*role_names: str):
    """View decorator: 401/redirect if unauthenticated, 403 if wrong role."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not has_role(request.user, *role_names):
                raise PermissionDenied("Your role does not have access to this page.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
