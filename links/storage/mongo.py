from __future__ import annotations

from datetime import date, datetime
from datetime import timezone as dt_timezone

from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

from .base import CodeTaken, LinkRecord, LinkStore


def _aware(value: datetime | None) -> datetime | None:
    """Mongo hands back naive UTC datetimes; Django expects aware ones."""
    if value is None:
        return None
    return value.replace(tzinfo=dt_timezone.utc) if value.tzinfo is None else value


class MongoLinkStore(LinkStore):
    name = "mongo"

    def __init__(self, uri: str, db_name: str, timeout_ms: int) -> None:
        self.client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms)
        self.client.admin.command("ping")
        db = self.client[db_name]
        self.links = db["links"]
        self.clicks = db["clicks"]
        self.links.create_index([("tenant_id", ASCENDING), ("code", ASCENDING)], unique=True)
        self.clicks.create_index(
            [("tenant_id", ASCENDING), ("code", ASCENDING), ("at", ASCENDING)]
        )

    def _to_record(self, doc: dict) -> LinkRecord:
        return LinkRecord(
            tenant_id=doc["tenant_id"],
            code=doc["code"],
            target_url=doc["target_url"],
            created_at=_aware(doc["created_at"]),
            expires_at=_aware(doc.get("expires_at")),
        )

    def _insert(self, record: LinkRecord) -> None:
        try:
            self.links.insert_one(
                {
                    "tenant_id": record.tenant_id,
                    "code": record.code,
                    "target_url": record.target_url,
                    "created_at": record.created_at,
                    "expires_at": record.expires_at,
                }
            )
        except DuplicateKeyError as exc:
            raise CodeTaken(record.code) from exc

    def get_link(self, tenant_id: int, code: str) -> LinkRecord | None:
        doc = self.links.find_one({"tenant_id": tenant_id, "code": code})
        return self._to_record(doc) if doc else None

    def list_links(self, tenant_id: int) -> list[LinkRecord]:
        docs = self.links.find({"tenant_id": tenant_id}).sort("created_at", -1)
        return [self._to_record(doc) for doc in docs]

    def delete_link(self, tenant_id: int, code: str) -> bool:
        result = self.links.delete_one({"tenant_id": tenant_id, "code": code})
        if result.deleted_count:
            self.clicks.delete_many({"tenant_id": tenant_id, "code": code})
        return bool(result.deleted_count)

    def record_click(
        self, tenant_id: int, code: str, at: datetime, referrer: str, user_agent: str
    ) -> None:
        self.clicks.insert_one(
            {
                "tenant_id": tenant_id,
                "code": code,
                "at": at,
                "referrer": referrer,
                "user_agent": user_agent,
            }
        )

    def click_totals(self, tenant_id: int) -> dict[str, int]:
        pipeline = [
            {"$match": {"tenant_id": tenant_id}},
            {"$group": {"_id": "$code", "total": {"$sum": 1}}},
        ]
        return {row["_id"]: row["total"] for row in self.clicks.aggregate(pipeline)}

    def click_total(self, tenant_id: int, code: str) -> int:
        return self.clicks.count_documents({"tenant_id": tenant_id, "code": code})

    def clicks_by_day(self, tenant_id: int, code: str, since: datetime) -> dict[date, int]:
        pipeline = [
            {"$match": {"tenant_id": tenant_id, "code": code, "at": {"$gte": since}}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$at"}},
                    "total": {"$sum": 1},
                }
            },
        ]
        return {
            date.fromisoformat(row["_id"]): row["total"]
            for row in self.clicks.aggregate(pipeline)
        }

    def delete_tenant_data(self, tenant_id: int) -> None:
        self.links.delete_many({"tenant_id": tenant_id})
        self.clicks.delete_many({"tenant_id": tenant_id})
