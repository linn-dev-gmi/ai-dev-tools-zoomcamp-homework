from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from tenants.models import Membership, Tenant

from .models import ClickEvent, Link
from .storage import CodeTaken, LinkRecord, get_store, reset_store

User = get_user_model()


@override_settings(MONGO_URI="")
class StoreTestCase(TestCase):
    def setUp(self):
        reset_store()
        self.store = get_store()
        self.acme = Tenant.objects.create(slug="acme", name="Acme")
        self.globex = Tenant.objects.create(slug="globex", name="Globex")

    def tearDown(self):
        reset_store()

    def make_link(self, tenant, code="", url="https://example.com", expires_at=None):
        return self.store.create_link(
            LinkRecord(
                tenant_id=tenant.id,
                code=code,
                target_url=url,
                created_at=timezone.now(),
                expires_at=expires_at,
            )
        )


class StorageIsolationTests(StoreTestCase):
    def test_same_code_belongs_to_each_tenant_separately(self):
        self.make_link(self.acme, code="xY9", url="https://acme.test")
        self.make_link(self.globex, code="xY9", url="https://globex.test")

        self.assertEqual(self.store.get_link(self.acme.id, "xY9").target_url, "https://acme.test")
        self.assertEqual(
            self.store.get_link(self.globex.id, "xY9").target_url, "https://globex.test"
        )

    def test_duplicate_code_within_one_tenant_is_rejected(self):
        self.make_link(self.acme, code="xY9")
        with self.assertRaises(CodeTaken):
            self.make_link(self.acme, code="xY9")

    def test_listing_never_crosses_tenants(self):
        self.make_link(self.acme, code="a1")
        self.make_link(self.globex, code="b2")

        self.assertEqual([link.code for link in self.store.list_links(self.acme.id)], ["a1"])
        self.assertEqual([link.code for link in self.store.list_links(self.globex.id)], ["b2"])

    def test_delete_does_not_reach_another_tenants_link(self):
        self.make_link(self.globex, code="b2")

        self.assertFalse(self.store.delete_link(self.acme.id, "b2"))
        self.assertIsNotNone(self.store.get_link(self.globex.id, "b2"))

    def test_click_counts_are_scoped_per_tenant(self):
        self.make_link(self.acme, code="xY9")
        self.make_link(self.globex, code="xY9")
        self.store.record_click(self.acme.id, "xY9", timezone.now(), "", "")
        self.store.record_click(self.acme.id, "xY9", timezone.now(), "", "")
        self.store.record_click(self.globex.id, "xY9", timezone.now(), "", "")

        self.assertEqual(self.store.click_total(self.acme.id, "xY9"), 2)
        self.assertEqual(self.store.click_total(self.globex.id, "xY9"), 1)
        self.assertEqual(self.store.click_totals(self.acme.id), {"xY9": 2})


class StorageBehaviourTests(StoreTestCase):
    def test_blank_code_gets_a_generated_one(self):
        created = self.make_link(self.acme)

        self.assertTrue(created.code)
        self.assertIsNotNone(self.store.get_link(self.acme.id, created.code))

    def test_deleting_a_link_drops_its_clicks(self):
        self.make_link(self.acme, code="a1")
        self.store.record_click(self.acme.id, "a1", timezone.now(), "", "")

        self.store.delete_link(self.acme.id, "a1")

        self.assertEqual(self.store.click_total(self.acme.id, "a1"), 0)

    def test_clicks_by_day_buckets_by_date(self):
        self.make_link(self.acme, code="a1")
        now = timezone.now()
        self.store.record_click(self.acme.id, "a1", now, "", "")
        self.store.record_click(self.acme.id, "a1", now, "", "")
        self.store.record_click(self.acme.id, "a1", now - timedelta(days=1), "", "")

        counts = self.store.clicks_by_day(self.acme.id, "a1", now - timedelta(days=7))

        self.assertEqual(counts[timezone.localdate()], 2)
        self.assertEqual(counts[timezone.localdate() - timedelta(days=1)], 1)

    def test_deleting_a_tenant_purges_its_links_and_clicks(self):
        self.make_link(self.acme, code="a1")
        self.make_link(self.globex, code="b2")
        self.store.record_click(self.acme.id, "a1", timezone.now(), "", "")
        acme_id = self.acme.id

        self.acme.delete()

        self.assertEqual(Link.objects.filter(tenant_id=acme_id).count(), 0)
        self.assertEqual(ClickEvent.objects.filter(tenant_id=acme_id).count(), 0)
        self.assertEqual(len(self.store.list_links(self.globex.id)), 1)


class RedirectTests(StoreTestCase):
    def test_each_tenant_prefix_resolves_to_its_own_target(self):
        self.make_link(self.acme, code="xY9", url="https://acme.test/")
        self.make_link(self.globex, code="xY9", url="https://globex.test/")

        self.assertRedirects(
            self.client.get("/acme/xY9"), "https://acme.test/", fetch_redirect_response=False
        )
        self.assertRedirects(
            self.client.get("/globex/xY9"), "https://globex.test/", fetch_redirect_response=False
        )

    def test_redirect_records_a_click_with_referrer_and_agent(self):
        self.make_link(self.acme, code="xY9")

        self.client.get("/acme/xY9", HTTP_REFERER="https://ref.test/", HTTP_USER_AGENT="probe/1")

        click = ClickEvent.objects.get(tenant_id=self.acme.id, code="xY9")
        self.assertEqual(click.referrer, "https://ref.test/")
        self.assertEqual(click.user_agent, "probe/1")

    def test_expired_link_is_gone_and_records_no_click(self):
        self.make_link(self.acme, code="old", expires_at=timezone.now() - timedelta(minutes=1))

        response = self.client.get("/acme/old")

        self.assertEqual(response.status_code, 410)
        self.assertEqual(self.store.click_total(self.acme.id, "old"), 0)

    def test_unknown_code_is_404(self):
        self.assertEqual(self.client.get("/acme/nope").status_code, 404)

    def test_dashboard_routes_are_not_shadowed_by_the_redirect(self):
        user = User.objects.create_user("dana", password="pw")
        Membership.objects.create(user=user, tenant=self.acme)
        self.client.force_login(user)

        self.assertEqual(self.client.get("/app/acme/").status_code, 200)


class DashboardAccessTests(StoreTestCase):
    def setUp(self):
        super().setUp()
        self.dana = User.objects.create_user("dana", password="pw")
        Membership.objects.create(user=self.dana, tenant=self.acme)
        self.make_link(self.globex, code="secret", url="https://globex.test/")

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get("/app/acme/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_non_member_cannot_see_another_tenants_dashboard(self):
        self.client.force_login(self.dana)

        self.assertEqual(self.client.get("/app/globex/").status_code, 404)
        self.assertEqual(self.client.get("/app/globex/secret/stats/").status_code, 404)
        self.assertEqual(
            self.client.post("/app/globex/secret/delete/").status_code, 404
        )
        self.assertIsNotNone(self.store.get_link(self.globex.id, "secret"))

    def test_member_of_two_tenants_sees_both(self):
        Membership.objects.create(user=self.dana, tenant=self.globex)
        self.client.force_login(self.dana)

        self.assertEqual(self.client.get("/app/acme/").status_code, 200)
        self.assertEqual(self.client.get("/app/globex/").status_code, 200)

    def test_creating_a_link_scopes_it_to_the_url_tenant(self):
        self.client.force_login(self.dana)

        self.client.post("/app/acme/new/", {"target_url": "https://example.com/", "code": "mine"})

        self.assertIsNotNone(self.store.get_link(self.acme.id, "mine"))
        self.assertIsNone(self.store.get_link(self.globex.id, "mine"))

    def test_custom_slug_already_used_in_the_same_tenant_is_rejected(self):
        self.make_link(self.acme, code="taken")
        self.client.force_login(self.dana)

        response = self.client.post(
            "/app/acme/new/", {"target_url": "https://example.com/", "code": "taken"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already used")

    def test_a_slug_used_by_another_tenant_is_still_available(self):
        self.client.force_login(self.dana)

        response = self.client.post(
            "/app/acme/new/", {"target_url": "https://example.com/", "code": "secret"}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(self.store.get_link(self.acme.id, "secret"))
