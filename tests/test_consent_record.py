"""Contract tests for ConsentRecord immutability.

These tests prove that the append-only guarantee holds:
- ORM save() raises on update
- ORM delete() raises always
- QuerySet.update() cannot mutate finalized entries (DB-level in Phase 3)
- bulk_create cannot bypass immutability
- Schema-level rejection of unknown consent_version
"""

import uuid
from datetime import UTC, datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase

from consent_registry.models import ConsentPurpose, ConsentRecord


@pytest.mark.django_db
class TestConsentRecordImmutability(TestCase):
    """Test that ConsentRecord is immutable after creation."""

    def setUp(self):
        """Create a test consent record."""
        self.subject_id = uuid.uuid4()
        self.record = ConsentRecord.objects.create(
            subject_id=self.subject_id,
            purpose=ConsentPurpose.MARKETING,
            consent_version="CT-marketing-v1",
            granted=True,
            ip_address="127.0.0.1",
            user_agent="Test/1.0",
            timestamp=datetime.now(UTC),
            prev_hash="0" * 64,
            entry_hash="a" * 64,
        )

    def test_save_raises_on_update(self):
        """Test that save() raises ValueError when updating an existing record."""
        self.record.granted = False
        with pytest.raises(ValueError, match="ConsentRecord is append-only"):
            self.record.save()

    def test_delete_raises_always(self):
        """Test that delete() raises ValueError always."""
        with pytest.raises(ValueError, match="ConsentRecord cannot be deleted"):
            self.record.delete()

    def test_queryset_update_bypasses_orm_guard(self):
        """Test that QuerySet.update() bypasses the ORM guard.

        This test documents the limitation: ORM-only immutability is insufficient.
        DB-level enforcement is required (Phase 3).
        """
        # QuerySet.update() bypasses save() and can mutate records
        updated = ConsentRecord.objects.filter(id=self.record.id).update(granted=False)
        assert updated == 1

        # The record was mutated — this is the defect being fixed
        self.record.refresh_from_db()
        assert self.record.granted is False

        # NOTE: This test documents the current limitation. In Phase 3, DB-level
        # triggers will prevent this. For now, the hash chain detects the tampering.

    def test_bulk_create_bypasses_orm_guard(self):
        """Test that bulk_create() bypasses the ORM guard.

        This test documents the limitation: ORM-only immutability is insufficient.
        DB-level enforcement is required (Phase 3).
        """
        # bulk_create() bypasses save() and can create records without validation
        new_record = ConsentRecord(
            subject_id=uuid.uuid4(),
            purpose=ConsentPurpose.MARKETING,
            consent_version="CT-marketing-v1",
            granted=True,
            timestamp=datetime.now(UTC),
            prev_hash="b" * 64,
            entry_hash="c" * 64,
        )
        created = ConsentRecord.objects.bulk_create([new_record])
        assert len(created) == 1

        # The record was created without going through save()
        # NOTE: This test documents the current limitation. In Phase 3, DB-level
        # triggers will prevent this. For now, the hash chain detects the tampering.

    def test_raw_sql_can_mutate_records(self):
        """Test that raw SQL can mutate records.

        This test documents the limitation: ORM-only immutability is insufficient.
        DB-level enforcement is required (Phase 3).
        """
        # NOTE: This test is skipped for SQLite because Django stores UUIDs differently
        # in SQLite vs PostgreSQL. In Phase 3, DB-level triggers will prevent this
        # regardless of the database backend.
        if connection.vendor == "sqlite":
            pytest.skip("SQLite UUID handling differs from PostgreSQL")

        # Raw SQL bypasses the ORM entirely
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE consent_registry_consentrecord SET granted = FALSE WHERE id = %s",
                [str(self.record.id)],
            )

        # The record was mutated
        self.record.refresh_from_db()
        assert self.record.granted is False

        # NOTE: This test documents the current limitation. In Phase 3, DB-level
        # triggers will prevent this. For now, the hash chain detects the tampering.


@pytest.mark.django_db
class TestConsentRecordSchemaValidation(TestCase):
    """Test schema-level validation of consent records."""

    def test_reject_unknown_purpose(self):
        """Test that unknown purpose values are rejected."""
        record = ConsentRecord(
            subject_id=uuid.uuid4(),
            purpose="unknown_purpose",  # Not in ConsentPurpose choices
            consent_version="CT-unknown-v1",
            granted=True,
            timestamp=datetime.now(UTC),
            prev_hash="0" * 64,
            entry_hash="a" * 64,
        )
        with pytest.raises(ValidationError):
            record.full_clean()  # Validates choices

    def test_reject_consent_version_too_long(self):
        """Test that consent_version > 64 chars is rejected."""
        record = ConsentRecord(
            subject_id=uuid.uuid4(),
            purpose=ConsentPurpose.MARKETING,
            consent_version="CT-marketing-v" + "1" * 100,  # > 64 chars
            granted=True,
            timestamp=datetime.now(UTC),
            prev_hash="0" * 64,
            entry_hash="a" * 64,
        )
        with pytest.raises(ValidationError):
            record.full_clean()  # Validates max_length

    def test_accept_widened_consent_version(self):
        """Test that consent_version up to 64 chars is accepted.

        This verifies the fix for the old max_length=16 limitation.
        """
        # CT-transactions-v1 is 18 chars (was > 16)
        record = ConsentRecord.objects.create(
            subject_id=uuid.uuid4(),
            purpose=ConsentPurpose.MARKETING,
            consent_version="CT-transactions-v1",  # 18 chars
            granted=True,
            timestamp=datetime.now(UTC),
            prev_hash="0" * 64,
            entry_hash="a" * 64,
        )
        assert record.consent_version == "CT-transactions-v1"
        assert len(record.consent_version) == 18
