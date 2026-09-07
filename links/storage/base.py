from __future__ import annotations

import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import date, datetime

from django.utils import timezone

ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 7


class CodeTaken(Exception):
    """A link with this code already exists for this tenant."""


@dataclass(frozen=True)
class LinkRecord:
    tenant_id: int
    code: str
    target_url: str
    created_at: datetime
    expires_at: datetime | None = None

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


class LinkStore(ABC):
    """Every method takes tenant_id first; there is no way to query across tenants."""

    @abstractmethod
    def _insert(self, record: LinkRecord) -> None:
        """Insert, raising CodeTaken on a duplicate (tenant_id, code)."""

    @abstractmethod
    def get_link(self, tenant_id: int, code: str) -> LinkRecord | None: ...

    @abstractmethod
    def list_links(self, tenant_id: int) -> list[LinkRecord]: ...

    @abstractmethod
    def delete_link(self, tenant_id: int, code: str) -> bool: ...

    @abstractmethod
    def record_click(
        self, tenant_id: int, code: str, at: datetime, referrer: str, user_agent: str
    ) -> None: ...

    @abstractmethod
    def click_totals(self, tenant_id: int) -> dict[str, int]: ...

    @abstractmethod
    def click_total(self, tenant_id: int, code: str) -> int: ...

    @abstractmethod
    def clicks_by_day(self, tenant_id: int, code: str, since: datetime) -> dict[date, int]: ...

    @abstractmethod
    def delete_tenant_data(self, tenant_id: int) -> None: ...

    def create_link(self, record: LinkRecord) -> LinkRecord:
        """Insert `record`, generating a free code when it carries none."""
        if record.code:
            self._insert(record)
            return record
        for _ in range(10):
            candidate = replace(record, code=generate_code())
            try:
                self._insert(candidate)
            except CodeTaken:
                continue
            return candidate
        raise CodeTaken("Could not generate a free code.")
