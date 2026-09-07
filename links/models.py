from django.db import models

# tenant_id is a plain integer, not a ForeignKey: these two tables mirror the
# Mongo collections, which cannot reference the SQLite tenant table either.
# Tenant deletion purges them explicitly (see links.signals).


class Link(models.Model):
    tenant_id = models.PositiveIntegerField()
    code = models.CharField(max_length=64)
    target_url = models.URLField(max_length=2000)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant_id", "code"], name="unique_tenant_code")
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id}/{self.code}"


class ClickEvent(models.Model):
    tenant_id = models.PositiveIntegerField()
    code = models.CharField(max_length=64)
    at = models.DateTimeField()
    referrer = models.CharField(max_length=2000, blank=True)
    user_agent = models.CharField(max_length=1000, blank=True)

    class Meta:
        indexes = [models.Index(fields=["tenant_id", "code", "at"])]
