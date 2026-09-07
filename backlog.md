# Backlog

Derived from [`_docs/plan.md`](_docs/plan.md).

## Done

### 1. Scaffold the Django project and apps

Create the `config` project with `accounts`, `tenants` and `links` apps, register
them in `INSTALLED_APPS`, and swap in a custom `User` model before the first
migration — Django makes this painful to change later.

*Done when:* `manage.py check` passes and `AUTH_USER_MODEL` points at
`accounts.User`.

### 2. Tenant and Membership models

`Tenant` (slug, name) and `Membership` as a through-model, so one user can belong
to several workspaces. Reserved-slug validation keeps a tenant from claiming
`app`, `admin` or `accounts`. Both registered in the Django admin, which is how
workspaces get created — there is no self-serve signup.

*Done when:* a tenant and a membership can be created in the admin, and `acme`
can be created but `admin` cannot.

### 3. One place that decides tenant access

`tenants/access.py`: resolve the URL's tenant slug, confirm the logged-in user is
a member, attach it to the request. A non-member gets 404, not 403, so the app
never confirms that a workspace exists to an outsider.

*Done when:* every dashboard view is wrapped in it and none of them query
`Tenant` directly.

### 4. LinkStore interface and the SQLite implementation

Define the storage contract — `tenant_id` is the first argument of every method,
so a query that forgets the tenant cannot be written by accident. Implement it
over the Django ORM against `Link` and `ClickEvent`.

*Done when:* links can be created, fetched, listed and deleted per tenant, and
a blank code gets a generated one.

### 5. Mongo implementation and startup selection

The same contract over PyMongo, with a unique index on `(tenant_id, code)`.
Select the backend once from `MONGO_URI`; if Mongo is unset or unreachable, log
the downgrade and continue on SQLite instead of refusing to boot.

*Done when:* the app starts and serves links with Mongo unset, with Mongo set to
an unreachable host, and the active store is visible in the UI.

### 6. Public redirect with click capture

`/{tenant-slug}/{code}` resolves the tenant, looks up the link, records a click
with timestamp, referrer and user agent, and redirects. Expired links return 410
and record nothing. Registered last in the URLconf so it cannot shadow `/app/`.

*Done when:* the same code under two tenant prefixes reaches two destinations.

### 7. Dashboard: list, create, delete

Per-workspace link list, a create form with optional custom slug and expiry, and
delete. Slug uniqueness is validated per tenant, so a code taken in another
workspace is still available in yours.

*Done when:* a member can create, see and delete links, and a duplicate slug in
the same workspace is rejected with a form error.

### 8. Click analytics

Per-link total, plus clicks-per-day for the last 30 days rendered as a CSS bar
chart. The list view fetches all totals in one aggregate rather than per row.

*Done when:* the stats page shows a total and a 30-day series with the peak
labelled.

### 9. Cross-store integrity on tenant deletion

`Link` and `ClickEvent` hold `tenant_id` as a plain integer, because Mongo cannot
hold a foreign key into SQLite. A `post_delete` signal on `Tenant` purges its
links and clicks explicitly.

*Done when:* deleting a tenant leaves no orphaned links or clicks, and other
tenants are untouched.

### 10. Tests

Cover the isolation claims first: same code in two tenants, listing, delete and
stats not crossing a tenant boundary, a non-member getting 404. Then behaviour:
generated codes, expiry, click bucketing by day, tenant purge, page rendering.

*Done when:* `uv run python manage.py test` is green. Currently 22 tests.

### 11. Repo and docs

Public GitHub repo with `.gitignore`, `README.md`, `_docs/plan.md` and this file.
uv for dependency management, lockfile committed, `.env` ignored.

*Done when:* a clean clone runs `uv sync && uv run python manage.py migrate &&
uv run python manage.py runserver` without further setup.

## Not started

### 12. Run the Mongo backend against a real MongoDB

The Mongo implementation is written and the fallback path is exercised, but the
happy path has never been run against a live server — every test so far runs on
SQLite. Stand up Mongo, point `MONGO_URI` at it, and walk the app by hand.

*Done when:* links created with Mongo configured survive a restart and the
dashboard reports `store: mongo`.

### 13. Run the test suite against both backends

Parameterise the suite so it runs once per available backend, skipping Mongo when
it is not reachable. The plan does not require strict parity, but the isolation
guarantees must hold on both.

*Done when:* the isolation tests pass against Mongo as well as SQLite.

### 14. Pagination on the link list

The list fetches every link in a workspace. Fine for a demo, wrong past a few
hundred.

### 15. Roles and invites

Out of scope in the plan and still out of scope: a tenant is a flat set of users
added through the admin. Listed here so it is a decision rather than an omission.
