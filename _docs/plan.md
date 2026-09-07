# shortlink — plan

Multitenant URL shortener with click analytics. Django, Mongo-first with a SQLite
fallback.

This is the spec that came out of the brainstorm for homework 1. The course's
seed idea was deliberately vague and meant to be reshaped; this is where it
landed after narrowing the domain twice — first away from an inventory system,
then away from a full product — so that the effort goes into the architecture
rather than into breadth of features.

## What this homework is demonstrating

Three things, integrated:

1. A working Django app.
2. Tenant isolation.
3. Swappable persistence — the same app runs with or without Mongo.

The domain is deliberately small so the effort lands on 2 and 3. A URL shortener
is two models; anything bigger would have crowded them out.

## Decisions

### Tenancy

Path-prefixed, shared storage.

- Public redirect: `/{tenant-slug}/{code}`.
- Dashboard: `/app/{tenant-slug}/`, registered before the redirect so it is
  never shadowed by it.
- Every link and click row carries `tenant_id`.
- The prefix is a human slug, not a PK or UUID — a UUID makes a "short" link 40
  characters, and sequential integers leak the tenant count and invite walking
  them. A reserved-slug list keeps a tenant from claiming `app` or `admin`.
- Two tenants may own the same code. `/acme/xY9` and `/globex/xY9` are different
  links; that collision is the demo that isolation actually works.

Isolation is enforced in two places and only two. `tenants.access` decides
whether a user may act on a tenant at all, and every storage method takes
`tenant_id` as its first argument, so a query that forgets the tenant does not
type-check as a call. A non-member gets a 404 rather than a 403, so the
dashboard never confirms that a workspace exists to someone outside it.

Users may belong to several tenants; membership is a through-model, and the
header carries a switcher.

### Storage

Mongo is the real backend. SQLite is a fallback so a grader can run the app with
zero setup. **The two are not required to be at feature parity** — analytics
aggregation is allowed to be richer on Mongo.

| Data | Store |
|------|-------|
| Users, sessions, admin, tenants, membership | SQLite, always, via the Django ORM |
| Links, click events | Mongo when reachable; SQLite tables otherwise |

Auth and admin never move, so they just work. Only `Link` and `ClickEvent` go
through the storage abstraction: a `LinkStore` interface with a PyMongo
implementation and a Django ORM one. Selection happens once, lazily, from
`MONGO_URI`; if the connection fails the app logs the downgrade and continues on
SQLite rather than refusing to boot.

### Features

- Login; create, list, and delete short links scoped to your workspace.
- User-chosen custom slugs, unique per tenant.
- Link expiry — an expired link returns 410 instead of redirecting.
- Public redirect endpoint, recording each hit.
- Per-click capture: timestamp, referrer, user agent.
- Per-link total clicks, plus clicks-per-day for the last 30 days as a chart.

### Explicitly out of scope

Roles and invites (a tenant is a flat set of users). Self-serve signup, password
reset, email. QR codes. Bulk import. A REST API. Rate limiting. Bot filtering.
Geo/IP lookup. Charts beyond the single 30-day series.

## Risks

- **Cross-store integrity.** A link may live in Mongo while its owning tenant
  lives in SQLite, so no foreign key can tie them together. Both backends
  therefore store `tenant_id` as a plain integer, and a `post_delete` signal on
  `Tenant` purges its links and clicks explicitly.
- **Isolation leaks.** Shared storage means one missing `tenant_id` filter is a
  leak. Hence the two-chokepoint rule above, and tests that assert tenant A
  cannot reach tenant B's links by list, stats, delete or redirect.
- **Two code paths.** Every links/clicks query is written twice. This is the main
  cost of the fallback and the reason the domain is only two models.

## Stack

Django 6.1, Python 3.12, PyMongo, SQLite, uv. No Celery, no Redis, no Docker
requirement, no JS dependencies — the chart is CSS.

## Layout

    config/     settings, root urls
    accounts/   custom User model
    tenants/    Tenant, Membership, access rules
    links/      Link + ClickEvent, storage backends, views, redirect
    templates/
