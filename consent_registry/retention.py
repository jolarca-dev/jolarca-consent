"""Retention policy and anonymization for consent records.

Defines per-purpose retention TTLs and provides the anonymization logic
that implements ADR-0003 (anonymize-don't-delete) when the retention
period expires.

Design decisions:
- TTLs are measured from the record's `timestamp` (the time consent was
  given or withdrawn).
- Only withdrawn records (granted=False) are eligible for anonymization.
  Active grants are retained indefinitely — they are the proof of consent
  required by GDPR Art. 7(1). Anonymizing an active grant would destroy
  the controller's ability to demonstrate lawful processing.
- Anonymization replaces `subject_id` with an unlinkable UUID, clears
  `ip_address` and `user_agent`, and sets `anonymized_at`. The original
  `entry_hash` is preserved in the DB (the hash was computed over the
  original data before anonymization). The chain verifier skips
  entry_hash recomputation for anonymized records but still verifies
  prev_hash chain continuity.
- TTL values are `[COUNSEL-TO-CONFIRM]` — they must be confirmed by
  legal counsel before production deployment. The defaults below are
  conservative placeholders.
"""

import uuid
from datetime import UTC, datetime, timedelta

import structlog
from django.conf import settings
from django.db.models import QuerySet

from .models import ConsentPurpose, ConsentRecord

logger = structlog.get_logger(__name__)

# ── Retention TTLs per purpose class ────────────────────────────────────────
#
# Each value is the number of days after which a WITHDRAWN consent record
# is eligible for anonymization. The clock starts at the record's
# `timestamp` field (which for a withdrawal record is the withdrawal time).
#
# These are DEFAULTS. Override in Django settings via:
#   CONSENT_RETENTION_TTLS = {"marketing": 365, "location": 180, "ai": 180}
#
# All values are [COUNSEL-TO-CONFIRM] until legal counsel approves them.
_DEFAULT_RETENTION_TTLS: dict[str, int] = {
    ConsentPurpose.MARKETING: 730,  # 2 years — [COUNSEL-TO-CONFIRM]
    ConsentPurpose.LOCATION: 365,  # 1 year — [COUNSEL-TO-CONFIRM]
    ConsentPurpose.AI: 365,  # 1 year — [COUNSEL-TO-CONFIRM]
}


def get_retention_ttls() -> dict[str, int]:
    """Return the retention TTLs (in days) per purpose.

    Reads from Django settings ``CONSENT_RETENTION_TTLS`` if defined,
    otherwise falls back to the module defaults.

    Returns:
        Dictionary mapping purpose value (str) to retention days (int).
    """
    configured = getattr(settings, "CONSENT_RETENTION_TTLS", None)
    if configured is not None:
        return dict(configured)
    return dict(_DEFAULT_RETENTION_TTLS)


def get_expired_records(now: datetime | None = None) -> QuerySet[ConsentRecord]:
    """Return withdrawn consent records past their retention TTL.

    Only withdrawn records (granted=False) are eligible. Active grants
    are the proof of consent (Art. 7(1)) and must not be anonymized
    while consent is still in effect.

    Already-anonymized records (anonymized_at IS NOT NULL) are excluded.

    Args:
        now: Reference time for expiry calculation. Defaults to UTC now.

    Returns:
        QuerySet of ConsentRecord instances that are eligible for
        anonymization.
    """
    if now is None:
        now = datetime.now(UTC)

    ttls = get_retention_ttls()

    # Build a union of expired records across all purposes.
    # Each purpose has its own TTL, so we compute the cutoff date per
    # purpose and filter records with timestamp < cutoff.
    expired_pks: set[uuid.UUID] = set()
    for purpose, days in ttls.items():
        cutoff = now - timedelta(days=days)
        purpose_qs = ConsentRecord.objects.filter(
            purpose=purpose,
            granted=False,
            anonymized_at__isnull=True,
            timestamp__lt=cutoff,
        ).values_list("pk", flat=True)
        expired_pks.update(purpose_qs)

    return ConsentRecord.objects.filter(pk__in=expired_pks)


def anonymize_record(record: ConsentRecord, now: datetime | None = None) -> ConsentRecord:
    """Anonymize a single consent record (ADR-0003).

    Replaces personal data fields with unlinkable values:
    - subject_id → new random UUID (unlinkable to the original subject)
    - ip_address → None
    - user_agent → "" (empty string)
    - anonymized_at → current timestamp

    The original entry_hash is preserved in the DB. The hash chain
    verifier handles anonymized records by skipping entry_hash
    recomputation but still checking prev_hash continuity.

    Uses QuerySet.update() to bypass the ORM-level immutability guard
    (ConsentRecord.save() raises on update). Anonymization is an
    authorized administrative action, not a regular data modification.

    Args:
        record: The ConsentRecord to anonymize.
        now: Timestamp to set for anonymized_at. Defaults to UTC now.

    Returns:
        The refreshed ConsentRecord instance.

    Raises:
        ValueError: If the record is already anonymized.
    """
    if record.anonymized_at is not None:
        raise ValueError(f"Record {record.id} is already anonymized.")

    if now is None:
        now = datetime.now(UTC)

    new_subject_id = uuid.uuid4()

    # Use QuerySet.update() to bypass the ORM immutability guard.
    # This is the ONLY authorized path that modifies existing records.
    ConsentRecord.objects.filter(pk=record.pk).update(
        subject_id=new_subject_id,
        ip_address=None,
        user_agent="",
        anonymized_at=now,
    )

    logger.info(
        "consent_record_anonymized",
        record_id=str(record.id),
        purpose=record.purpose,
        original_subject_id_was=str(record.subject_id),
        anonymized_at=now.isoformat(),
    )

    record.refresh_from_db()
    return record


def anonymize_expired(now: datetime | None = None, purpose: str | None = None) -> int:
    """Anonymize all expired consent records.

    Finds all withdrawn records past their retention TTL and anonymizes
    them. Returns the count of anonymized records.

    Args:
        now: Reference time for expiry calculation. Defaults to UTC now.
        purpose: If provided, limit anonymization to this purpose class.

    Returns:
        Number of records anonymized.
    """
    if now is None:
        now = datetime.now(UTC)

    expired = get_expired_records(now=now)
    if purpose:
        expired = expired.filter(purpose=purpose)
    count = 0

    for record in expired:
        anonymize_record(record, now=now)
        count += 1

    if count > 0:
        logger.info(
            "retention_anonymization_complete",
            records_anonymized=count,
            reference_time=now.isoformat(),
        )
    else:
        logger.debug("retention_anonymization_no_expired_records", reference_time=now.isoformat())

    return count
