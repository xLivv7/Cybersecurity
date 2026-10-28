"""Validate limits before recording activity; all policy reads are current."""

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from apps.accounts.backends import password_expired

from .selectors import get_security_settings
from .services import ChangeReason
from .sessions import CONTEXT_KEY, get_access


def passive_view(view):
    """Automatic polling endpoints must opt out of extending user activity."""
    view.counts_as_activity = False
    return view


class SecurityContextMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        access = get_access(request)
        if access is None:
            if request.user.is_authenticated:
                auth.logout(request)
            return None
        user, data = access
        policy = get_security_settings()
        now = timezone.now()
        try:
            last_activity = datetime.fromisoformat(data["last_activity"])
            if timezone.is_naive(last_activity) or last_activity > now:
                raise ValueError
            if (now - last_activity) // timedelta(
                minutes=1
            ) >= policy.idle_timeout_minutes:
                raise ValueError
        except (KeyError, TypeError, ValueError):
            auth.logout(request)
            return redirect("accounts:login")
        if data["scope"] == "full" and password_expired(user, policy, now):
            data = {**data, "scope": "limited", "reason": ChangeReason.EXPIRED}
            auth.logout(request)
            request.session.cycle_key()
            request.session[CONTEXT_KEY] = data
        # Limited contexts cannot reach future application views accidentally.
        if data["scope"] == "limited" and request.resolver_match.view_name not in (
            "security:password_required",
            "accounts:logout",
        ):
            return redirect("security:password_required")
        if (
            not request.path.startswith(settings.STATIC_URL)
            and getattr(view_func, "counts_as_activity", True)
            and request.method in ("GET", "POST")
        ):
            request.session[CONTEXT_KEY] = {**data, "last_activity": now.isoformat()}
        return None
