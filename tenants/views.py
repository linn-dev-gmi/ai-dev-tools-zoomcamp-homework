from django.shortcuts import redirect, render

from .models import Tenant


def home(request):
    if not request.user.is_authenticated:
        return render(request, "home.html")
    tenants = Tenant.objects.filter(memberships__user=request.user)
    if tenants.count() == 1:
        return redirect("link_list", tenant_slug=tenants[0].slug)
    return render(request, "home.html", {"tenants": tenants})
