from __future__ import annotations

from datetime import date, datetime

from django.db import IntegrityError
from django.db.models import Count
from django.db.models.functions import TruncDate

from links.models import ClickEvent, Link

from .base import CodeTaken, LinkRecord, LinkStore


def _to_record(row: Link) -> LinkRecord:
    return LinkRecord(
        tenant_id=row.tenant_id,
        code=row.code,
        target_url=row.target_url,
        created_at=row.created_at,
        expires_at=row.expires_at,
    )


class SqliteLinkStore(LinkStore):
    name = "sqlite"

    def _insert(self, record: LinkRecord) -> None:
        try:
            Link.objects.create(
                tenant_id=record.tenant_id,
                code=record.code,
                target_url=record.target_url,
                created_at=record.created_at,
                expires_at=record.expires_at,
            )
        except IntegrityError as exc:
            raise CodeTaken(record.code) from exc

    def get_link(self, tenant_id: int, code: str) -> LinkRecord | None:
        row = Link.objects.filter(tenant_id=tenant_id, code=code).first()
        return _to_record(row) if row else None

    def list_links(self, tenant_id: int) -> list[LinkRecord]:
        rows = Link.objects.filter(tenant_id=tenant_id).order_by("-created_at")
        return [_to_record(row) for row in rows]

    def delete_link(self, tenant_id: int, code: str) -> bool:
        deleted, _ = Link.objects.filter(tenant_id=tenant_id, code=code).delete()
        if deleted:
            ClickEvent.objects.filter(tenant_id=tenant_id, code=code).delete()
        return bool(deleted)

    def record_click(
        self, tenant_id: int, code: str, at: datetime, referrer: str, user_agent: str
    ) -> None:
        ClickEvent.objects.create(
            tenant_id=tenant_id, code=code, at=at, referrer=referrer, user_agent=user_agent
        )

    def click_totals(self, tenant_id: int) -> dict[str, int]:
        rows = (
            ClickEvent.objects.filter(tenant_id=tenant_id)
            .values("code")
            .annotate(total=Count("id"))
        )
        return {row["code"]: row["total"] for row in rows}

    def click_total(self, tenant_id: int, code: str) -> int:
        return ClickEvent.objects.filter(tenant_id=tenant_id, code=code).count()

    def clicks_by_day(self, tenant_id: int, code: str, since: datetime) -> dict[date, int]:
        rows = (
            ClickEvent.objects.filter(tenant_id=tenant_id, code=code, at__gte=since)
            .annotate(day=TruncDate("at"))
            .values("day")
            .annotate(total=Count("id"))
        )
        return {row["day"]: row["total"] for row in rows}

    def delete_tenant_data(self, tenant_id: int) -> None:
        Link.objects.filter(tenant_id=tenant_id).delete()
        ClickEvent.objects.filter(tenant_id=tenant_id).delete()
