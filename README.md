# shortlink

A multitenant URL shortener with click analytics, built with Django.

Each workspace owns its own short links under its own prefix, so `/acme/xY9` and
`/globex/xY9` are two different links belonging to two different tenants. Links
and click events live in MongoDB when it is configured, and fall back to SQLite
when it is not, so the app runs with zero setup.

Built for [AI Dev Tools Zoomcamp 2026](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp),
homework 1. The spec this was built from is in [`_docs/plan.md`](_docs/plan.md), and
the task breakdown is in [`backlog.md`](backlog.md).

## Features

- **Multitenancy.** A user can belong to several workspaces and switch between
  them. Every link and click row carries a `tenant_id`, and every storage call
  takes the tenant as its first argument, so there is no way to query across
  tenants by accident.
- **Custom slugs.** Choose your own short code or get a generated one. Codes are
  unique per workspace, not globally, so two tenants can both use `launch`.
- **Expiry.** A link can be given an expiry date; past it, the redirect returns
  410 Gone instead of forwarding.
- **Click analytics.** Every hit records a timestamp, referrer and user agent.
  Each link has a total and a 30-day-per-day chart.
- **Swappable storage.** Mongo when reachable, SQLite otherwise, decided once at
  startup and logged.

## Quickstart

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Open http://127.0.0.1:8000/admin/ and create a `Tenant` (say slug `acme`), then a
`Membership` linking your user to it. Your dashboard is at
http://127.0.0.1:8000/app/acme/, and short links resolve at `/acme/<code>`.

## Storage

Copy `.env.example` to `.env` to point at Mongo:

```
MONGO_URI=mongodb://localhost:27017
MONGO_DB=shortlink
```

Leave `MONGO_URI` unset, or point it at a host that is down, and the app logs the
downgrade and serves links from SQLite instead. Users, sessions, workspaces and
the admin always live in SQLite through the Django ORM — only links and click
events move. The workspace dashboard shows which store is live.

The two backends are not held to strict parity; the split is the point, not a
guarantee that Mongo and SQLite behave identically under load.

## Tests

```bash
uv run python manage.py test
```

20 tests. The ones that matter cover tenant isolation: that a non-member gets a
404 rather than a 403 on another workspace, that the same code in two tenants
resolves to two different destinations, and that delete and stats cannot reach
across a tenant boundary.

## Layout

```
config/      settings, root URLs
accounts/    custom User model
tenants/     Tenant, Membership, and the single place access is decided
links/       Link and ClickEvent, the two storage backends, views
templates/
_docs/       the spec this was built from
```
