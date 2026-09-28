"""ConsentRecord model — the append-only consent ledger.

This model is the system of record for consent in the Journey of Life marketplace.
Records are immutable after creation. Withdrawal creates a NEW record with
granted=False; the original grant record is never modified or deleted (ADR-0003).

Key design decisions:
- subject_id is a UUID (not a FK to User) — this is an independent service
- consent_version is widened to max_length=64 (was 16 in the old model)
- purpose taxonomy aligns with jolarca-compliance/lawful-basis/consent-versions.md
- save() raises on update (ORM-level immutability; DB-level in Phase 3)
"""

import uuid
from typing import Any, NoReturn

from django.db import models


class ConsentPurpose(models.TextChoices):
    """Approved consent purposes.

    Aligned with jolarca-compliance/lawful-basis/consent-versions.md.
    Each purpose maps to one or more CT-<purpose>-v<N> consent texts.
    """

    MARKETING = "marketing", "Marketing communications"
    LOCATION = "location", "Geolocation search (ROPA-006)"
    AI = "ai", "Optional AI features (ROPA-005)"


class ConsentRecord(models.Model):
    """Immutable consent ledger (GDPR Art. 7).

    Records are never updated — a revocation is a NEW row with granted=False.
    The hash chain (prev_hash, entry_hash) provides tamper-evidence (ADR-0002).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the consent subject (user). Not a FK — this is an independent service.",
    )
    purpose = models.CharField(
        max_length=32,
        choices=ConsentPurpose.choices,
        help_text="Purpose of the consent (aligned with lawful-basis/consent-versions.md)",
    )
    consent_version = models.CharField(
        max_length=64,
        help_text="Consent text version (e.g., CT-marketing-v1). Widened from old max_length=16.",
    )
    granted = models.BooleanField(help_text="True if consent was granted, False if withdrawn")
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address at time of consent",
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        help_text="User agent at time of consent",
    )
    timestamp = models.DateTimeField(
        help_text="Timestamp when consent was given/withdrawn",
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when consent was revoked (if withdrawn)",
    )
    prev_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of the previous record in the chain (genesis: 64 zeros)",
    )
    entry_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA-256 hash of this record (canonical serialization)",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Record creation timestamp")

    class Meta:
        """Model metadata."""

        ordering = ["timestamp"]
        indexes = [
            models.Index(fields=["subject_id", "purpose"]),
            models.Index(fields=["purpose", "consent_version"]),
        ]
        # Table name for backward compatibility with migration plan
        db_table = "consent_registry_consentrecord"

    def __str__(self) -> str:
        """Human-readable representation."""
        action = "granted" if self.granted else "withdrawn"
        return f"ConsentRecord({self.subject_id}, {self.purpose}, {action})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Enforce append-only at ORM level.

        Raises ValueError if attempting to update an existing record.
        Use _state.adding to distinguish insert from update (UUID pk is set at instantiation).
        """
        if not self._state.adding:
            raise ValueError(
                "ConsentRecord is append-only; create a new record instead of updating."
            )
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Prevent deletion at ORM level.

        Raises ValueError always. Consent records are never deleted (ADR-0003).
        """
        raise ValueError("ConsentRecord cannot be deleted (ADR-0003: anonymize-don't-delete).")
