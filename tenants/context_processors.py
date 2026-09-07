from .models import Tenant


def memberships(request):
    if not request.user.is_authenticated:
        return {"user_tenants": []}
    return {"user_tenants": Tenant.objects.filter(memberships__user=request.user)}
