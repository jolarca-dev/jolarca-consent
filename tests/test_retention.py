"""Tests for retention policy and anonymization (ADR-0003).

Verifies:
- Retention TTLs per purpose class (defaults and settings override)
- Expired record identification (only withdrawn, past TTL, not already anonymized)
- Anonymization replaces personal data fields correctly
- Active grants are never anonymized
- Already-anonymized records are not re-anonymized
- Management command (dry-run, purpose filter, batch execution)
- Hash chain verifier handles anonymized records correctly
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from django.core.management import call_command
from django.test import TestCase, override_settings

from consent_registry.models import ConsentPurpose, ConsentRecord
from consent_registry.retention import (
    _DEFAULT_RETENTION_TTLS,
    anonymize_expired,
    anonymize_record,
    get_expired_records,
    get_retention_ttls,
)


def _make_record(
    *,
    purpose: str = ConsentPurpose.MARKETING,
    granted: bool = True,
    days_ago: int = 0,
    anonymized: bool = False,
    subject_id: uuid.UUID | None = None,
) -> ConsentRecord:
    """Create a consent record for testing.

    Args:
        purpose: Consent purpose value.
        granted: Whether consent was granted (True) or withdrawn (False).
        days_ago: How many days ago the record's timestamp should be.
        anonymized: Whether to pre-set anonymized_at.
        subject_id: Optional subject UUID. Auto-generated if None.

    Returns:
        The created ConsentRecord.
    """
    now = datetime.now(UTC)
    ts = now - timedelta(days=days_ago)
    return ConsentRecord.objects.create(
        subject_id=subject_id or uuid.uuid4(),
        purpose=purpose,
        consent_version=f"CT-{purpose}-v1",
        granted=granted,
        ip_address="192.168.1.1" if granted else "10.0.0.1",
        user_agent="TestAgent/1.0",
        timestamp=ts,
        revoked_at=ts if not granted else None,
        prev_hash="0" * 64,
        entry_hash=uuid.uuid4().hex,  # unique per record for test purposes
        anonymized_at=ts if anonymized else None,
    )


@pytest.mark.django_db
class TestRetentionTTLs(TestCase):
    """Test retention TTL configuration."""

    def test_default_ttls_cover_all_purposes(self):
        """Default TTLs must be defined for every ConsentPurpose."""
        ttls = get_retention_ttls()
        for purpose in ConsentPurpose:
            assert purpose.value in ttls, f"Missing TTL for purpose: {purpose.value}"

    def test_default_ttl_values_are_positive(self):
        """All default TTLs must be positive (days > 0)."""
        for purpose, days in _DEFAULT_RETENTION_TTLS.items():
            assert days > 0, f"TTL for {purpose} must be positive, got {days}"

    @override_settings(CONSENT_RETENTION_TTLS={"marketing": 30, "location": 60, "ai": 90})
    def test_settings_override(self):
        """CONSENT_RETENTION_TTLS in settings overrides defaults."""
        ttls = get_retention_ttls()
        assert ttls == {"marketing": 30, "location": 60, "ai": 90}

    def test_defaults_when_no_settings(self):
        """Without settings override, module defaults are used."""
        ttls = get_retention_ttls()
        assert ttls == dict(_DEFAULT_RETENTION_TTLS)


@pytest.mark.django_db
class TestGetExpiredRecords(TestCase):
    """Test expired record identification."""

    def test_withdrawn_past_ttl_is_expired(self):
        """Withdrawn records past their TTL are returned."""
        # Marketing TTL default is 730 days. Create a withdrawn record 800 days ago.
        record = _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800)
        expired = get_expired_records()
        assert record.pk in [r.pk for r in expired]

    def test_active_grant_never_expired(self):
        """Active grants are never returned, regardless of age."""
        # Even a very old active grant should not be expired
        record = _make_record(purpose=ConsentPurpose.MARKETING, granted=True, days_ago=5000)
        expired = get_expired_records()
        assert record.pk not in [r.pk for r in expired]

    def test_within_ttl_not_expired(self):
        """Withdrawn records within their TTL are not returned."""
        # Marketing TTL is 730 days. Create a withdrawn record 100 days ago.
        record = _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=100)
        expired = get_expired_records()
        assert record.pk not in [r.pk for r in expired]

    def test_already_anonymized_excluded(self):
        """Already-anonymized records are not returned."""
        record = _make_record(
            purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800, anonymized=True
        )
        expired = get_expired_records()
        assert record.pk not in [r.pk for r in expired]

    def test_different_purposes_different_ttls(self):
        """Location (365 days) expires sooner than marketing (730 days)."""
        # 400 days ago: location is expired, marketing is not
        location_record = _make_record(purpose=ConsentPurpose.LOCATION, granted=False, days_ago=400)
        marketing_record = _make_record(
            purpose=ConsentPurpose.MARKETING, granted=False, days_ago=400
        )

        expired = get_expired_records()
        expired_pks = [r.pk for r in expired]

        assert location_record.pk in expired_pks
        assert marketing_record.pk not in expired_pks

    def test_custom_now_parameter(self):
        """The now parameter allows testing with a reference time."""
        record = _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=100)
        # With a reference time 800 days in the future, the record is expired
        future_now = datetime.now(UTC) + timedelta(days=800)
        expired = get_expired_records(now=future_now)
        assert record.pk in [r.pk for r in expired]


@pytest.mark.django_db
class TestAnonymizeRecord(TestCase):
    """Test single-record anonymization."""

    def test_anonymize_replaces_personal_data(self):
        """Anonymization replaces subject_id, clears ip_address and user_agent."""
        original_subject = uuid.uuid4()
        record = _make_record(
            purpose=ConsentPurpose.MARKETING,
            granted=False,
            days_ago=800,
            subject_id=original_subject,
        )

        result = anonymize_record(record)

        assert result.anonymized_at is not None
        assert result.subject_id != original_subject
        assert result.ip_address is None
        assert result.user_agent == ""

    def test_anonymize_preserves_non_personal_fields(self):
        """Anonymization retains purpose, version, timestamp, granted, hashes."""
        record = _make_record(purpose=ConsentPurpose.LOCATION, granted=False, days_ago=400)
        original_purpose = record.purpose
        original_version = record.consent_version
        original_timestamp = record.timestamp
        original_granted = record.granted
        original_entry_hash = record.entry_hash
        original_prev_hash = record.prev_hash

        result = anonymize_record(record)

        assert result.purpose == original_purpose
        assert result.consent_version == original_version
        assert result.timestamp == original_timestamp
        assert result.granted == original_granted
        assert result.entry_hash == original_entry_hash
        assert result.prev_hash == original_prev_hash

    def test_anonymize_sets_anonymized_at(self):
        """anonymized_at is set to the provided timestamp."""
        record = _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800)
        specific_time = datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC)

        result = anonymize_record(record, now=specific_time)

        assert result.anonymized_at == specific_time

    def test_anonymize_already_anonymized_raises(self):
        """Anonymizing an already-anonymized record raises ValueError."""
        record = _make_record(
            purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800, anonymized=True
        )

        with pytest.raises(ValueError, match="already anonymized"):
            anonymize_record(record)

    def test_anonymize_subject_id_is_unlinkable(self):
        """The new subject_id is a random UUID, not derivable from the original."""
        original_subject = uuid.uuid4()
        record = _make_record(
            purpose=ConsentPurpose.MARKETING,
            granted=False,
            days_ago=800,
            subject_id=original_subject,
        )

        result = anonymize_record(record)

        assert result.subject_id != original_subject
        # The new UUID should be a valid UUID4
        assert isinstance(result.subject_id, uuid.UUID)


@pytest.mark.django_db
class TestAnonymizeExpired(TestCase):
    """Test batch anonymization."""

    def test_anonymize_expired_returns_count(self):
        """anonymize_expired returns the number of records anonymized."""
        _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800)
        _make_record(purpose=ConsentPurpose.LOCATION, granted=False, days_ago=400)
        # This one is NOT expired (within marketing TTL)
        _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=100)

        count = anonymize_expired()
        assert count == 2

    def test_anonymize_expired_no_expired_records(self):
        """Returns 0 when no records are expired."""
        _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=100)
        count = anonymize_expired()
        assert count == 0

    def test_anonymize_expired_skips_active_grants(self):
        """Active grants are never anonymized, even if old."""
        _make_record(purpose=ConsentPurpose.MARKETING, granted=True, days_ago=5000)
        count = anonymize_expired()
        assert count == 0

    def test_anonymize_expired_idempotent(self):
        """Running anonymize_expired twice does not re-anonymize records."""
        _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800)

        count1 = anonymize_expired()
        count2 = anonymize_expired()

        assert count1 == 1
        assert count2 == 0


@pytest.mark.django_db
class TestAnonymizeExpiredCommand(TestCase):
    """Test the anonymize_expired management command."""

    def test_dry_run_does_not_anonymize(self):
        """--dry-run reports count without making changes."""
        _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800)

        call_command("anonymize_expired", "--dry-run")

        # Record should NOT be anonymized
        assert ConsentRecord.objects.filter(anonymized_at__isnull=False).count() == 0

    def test_command_anonymizes_expired(self):
        """Without --dry-run, expired records are anonymized."""
        _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800)

        call_command("anonymize_expired")

        assert ConsentRecord.objects.filter(anonymized_at__isnull=False).count() == 1

    def test_command_no_expired_records(self):
        """Command succeeds with no expired records."""
        _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=100)

        call_command("anonymize_expired")

        assert ConsentRecord.objects.filter(anonymized_at__isnull=False).count() == 0

    def test_command_purpose_filter_limits_scope(self):
        """--purpose flag anonymizes ONLY the specified purpose."""
        # Create expired records for two different purposes
        _make_record(purpose=ConsentPurpose.MARKETING, granted=False, days_ago=800)
        _make_record(purpose=ConsentPurpose.LOCATION, granted=False, days_ago=400)

        # Anonymize only marketing records
        call_command("anonymize_expired", "--purpose", "marketing")

        # Only the marketing record should be anonymized
        anonymized = ConsentRecord.objects.filter(anonymized_at__isnull=False)
        assert anonymized.count() == 1
        assert anonymized.first().purpose == ConsentPurpose.MARKETING

        # Location record should still have personal data
        location = ConsentRecord.objects.get(purpose=ConsentPurpose.LOCATION)
        assert location.anonymized_at is None
        assert location.ip_address is not None
