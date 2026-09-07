from __future__ import annotations

import logging

from django.conf import settings
from pymongo.errors import PyMongoError

from .base import CodeTaken, LinkRecord, LinkStore
from .sqlite import SqliteLinkStore

logger = logging.getLogger(__name__)

_store: LinkStore | None = None


def _build_store() -> LinkStore:
    if not settings.MONGO_URI:
        logger.info("MONGO_URI is unset - links and clicks are on SQLite.")
        return SqliteLinkStore()

    from .mongo import MongoLinkStore

    try:
        store = MongoLinkStore(settings.MONGO_URI, settings.MONGO_DB, settings.MONGO_TIMEOUT_MS)
    except PyMongoError as exc:
        logger.warning("Mongo is unreachable (%s) - degrading to SQLite.", exc)
        return SqliteLinkStore()
    logger.info("Links and clicks are on Mongo database %s.", settings.MONGO_DB)
    return store


def get_store() -> LinkStore:
    global _store
    if _store is None:
        _store = _build_store()
    return _store


def reset_store() -> None:
    global _store
    _store = None


__all__ = ["CodeTaken", "LinkRecord", "LinkStore", "get_store", "reset_store"]
