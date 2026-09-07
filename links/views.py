from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from tenants.access import tenant_view
from tenants.models import Tenant

from .forms import LinkForm
from .storage import CodeTaken, LinkRecord, get_store

CHART_DAYS = 30


@tenant_view
def link_list(request):
    store = get_store()
    totals = store.click_totals(request.tenant.id)
    links = [
        {"link": link, "clicks": totals.get(link.code, 0)}
        for link in store.list_links(request.tenant.id)
    ]
    return render(request, "links/list.html", {"rows": links, "backend": store.name})


@tenant_view
def link_create(request):
    store = get_store()
    form = LinkForm(request.POST or None, tenant_id=request.tenant.id)
    if request.method == "POST" and form.is_valid():
        record = LinkRecord(
            tenant_id=request.tenant.id,
            code=form.cleaned_data["code"],
            target_url=form.cleaned_data["target_url"],
            created_at=timezone.now(),
            expires_at=form.cleaned_data["expires_at"],
        )
        try:
            created = store.create_link(record)
        except CodeTaken:
            form.add_error("code", "That slug is already used in this workspace.")
        else:
            messages.success(request, f"Created /{request.tenant.slug}/{created.code}")
            return redirect("link_list", tenant_slug=request.tenant.slug)
    return render(request, "links/form.html", {"form": form})


@tenant_view
@require_POST
def link_delete(request, code: str):
    if not get_store().delete_link(request.tenant.id, code):
        raise Http404
    messages.success(request, f"Deleted /{request.tenant.slug}/{code}")
    return redirect("link_list", tenant_slug=request.tenant.slug)


@tenant_view
def link_stats(request, code: str):
    store = get_store()
    link = store.get_link(request.tenant.id, code)
    if link is None:
        raise Http404

    today = timezone.localdate()
    since = timezone.now() - timedelta(days=CHART_DAYS - 1)
    counts = store.clicks_by_day(request.tenant.id, code, since)
    days = [today - timedelta(days=offset) for offset in range(CHART_DAYS - 1, -1, -1)]
    peak = max(counts.values(), default=0)
    series = [
        {"day": day, "count": counts.get(day, 0), "height": _bar_height(counts.get(day, 0), peak)}
        for day in days
    ]

    return render(
        request,
        "links/stats.html",
        {
            "link": link,
            "total": store.click_total(request.tenant.id, code),
            "series": series,
            "peak": peak,
            "days": CHART_DAYS,
            "first_day": days[0],
            "last_day": days[-1],
        },
    )


def _bar_height(count: int, peak: int) -> int:
    return round(100 * count / peak) if peak else 0


def follow_link(request, tenant_slug: str, code: str):
    tenant = get_object_or_404(Tenant, slug=tenant_slug)
    store = get_store()
    link = store.get_link(tenant.id, code)
    if link is None:
        raise Http404
    if link.is_expired:
        return HttpResponse("This link has expired.", status=410)

    store.record_click(
        tenant.id,
        code,
        timezone.now(),
        request.META.get("HTTP_REFERER", "")[:2000],
        request.META.get("HTTP_USER_AGENT", "")[:1000],
    )
    return HttpResponseRedirect(link.target_url)
