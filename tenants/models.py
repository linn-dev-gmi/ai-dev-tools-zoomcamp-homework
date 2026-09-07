from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

RESERVED_SLUGS = {"admin", "accounts", "app", "static", "media", "api"}


def validate_tenant_slug(value: str) -> None:
    if value in RESERVED_SLUGS:
        raise ValidationError(f"'{value}' is reserved and cannot be a tenant slug.")


class Tenant(models.Model):
    slug = models.SlugField(max_length=50, unique=True, validators=[validate_tenant_slug])
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.slug


class Membership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "tenant"], name="unique_user_tenant")
        ]
        ordering = ["tenant__slug"]

    def __str__(self) -> str:
        return f"{self.user} @ {self.tenant}"
