"""Independent optional hosting-panel credential, never the commercial account.

A technical account grants no permission without CURRENT matching Console
entitlement. Enrollment requires an already-authorized Console SSO session.
No provider password, customer Console password or plaintext secret is stored.
"""
from django.db import models


class HostingTechnicalLogin(models.Model):
    service_id = models.PositiveBigIntegerField(unique=True)
    subject_id = models.PositiveBigIntegerField()
    binding_ref = models.UUIDField()
    username = models.CharField(max_length=32, unique=True)
    password_hash = models.CharField(max_length=256)
    enabled = models.BooleanField(default=False)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    changed_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["subject_id", "service_id"], name="opanel_tech_owner_ix")]

    def __str__(self):
        return f"Hosting technical login #{self.service_id}"


class HostingLoginThrottle(models.Model):
    """Durable HMAC-keyed login limiter; stores no IP address or username."""
    fingerprint = models.CharField(max_length=64, primary_key=True)
    failure_count = models.PositiveSmallIntegerField(default=0)
    window_started = models.DateTimeField()
    locked_until = models.DateTimeField(null=True, blank=True)
