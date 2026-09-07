"""The single place tenant access is decided."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404

from .models import Tenant


def get_member_tenant(user, slug: str) -> Tenant:
    """Return the tenant, or 404 if it does not exist or the user is not a member.

    Non-membership is a 404 rather than a 403 so the dashboard never confirms
    that a tenant slug exists to someone outside it.
    """
    tenant = get_object_or_404(Tenant, slug=slug)
    if not tenant.memberships.filter(user=user).exists():
        raise Http404
    return tenant


def tenant_view(view):
    """Resolve `tenant_slug` to `request.tenant` and drop the kwarg."""

    @wraps(view)
    @login_required
    def wrapper(request, tenant_slug, *args, **kwargs):
        request.tenant = get_member_tenant(request.user, tenant_slug)
        return view(request, *args, **kwargs)

    return wrapper
