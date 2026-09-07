from django.db.models.signals import post_delete
from django.dispatch import receiver

from tenants.models import Tenant

from .storage import get_store


@receiver(post_delete, sender=Tenant)
def purge_tenant_links(sender, instance: Tenant, **kwargs) -> None:
    get_store().delete_tenant_data(instance.id)
