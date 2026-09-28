"""Adversarial test suite — prove every tampering path is detected.

These tests prove that the hash chain detects every tampering attempt:
1. Modifying a record's data (breaks entry_hash)
2. Modifying a record's prev_hash (breaks chain)
3. Deleting a record (breaks chain)
4. Inserting a record in the middle (breaks chain)
5. Reordering records (breaks chain)

These tests use the API endpoint to verify the chain, simulating what the
offline verifier and CI job would do.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from consent_integrity.hash_chain import compute_entry_hash, get_genesis_prev_hash
from consent_registry.models import ConsentPurpose, ConsentRecord


# Disable authentication for tests
@override_settings(
    REST_FRAMEWORK={
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        "DEFAULT_AUTHENTICATION_CLASSES": [],
        "DEFAULT_PERMISSION_CLASSES": [],
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
        ],
        "DEFAULT_PARSER_CLASSES": [
            "rest_framework.parsers.JSONParser",
        ],
    }
)
@pytest.mark.django_db
class TestAdversarialChainVerification(TestCase):
    """Test that the hash chain detects every tampering attempt."""

    def setUp(self):
        """Set up test client and create a valid chain."""
        self.client = APIClient()
        self.subject_id = uuid.uuid4()
        self.now = datetime.now(UTC)

        # Create a valid chain with 3 records
        self.records = []
        prev_hash = get_genesis_prev_hash()

        for i in range(3):
            timestamp = self.now + timedelta(minutes=i)
            record_data = {
                "subject_id": str(self.subject_id),
                "purpose": ConsentPurpose.MARKETING,
                "consent_version": "CT-marketing-v1",
                "granted": True,
                "ip_address": "127.0.0.1",
                "user_agent": "Test/1.0",
                "timestamp": timestamp.isoformat(),
                "revoked_at": None,
                "prev_hash": prev_hash,
            }
            entry_hash = compute_entry_hash(record_data)

            record = ConsentRecord.objects.create(
                subject_id=self.subject_id,
                purpose=ConsentPurpose.MARKETING,
                consent_version="CT-marketing-v1",
                granted=True,
                ip_address="127.0.0.1",
                user_agent="Test/1.0",
                timestamp=timestamp,
                prev_hash=prev_hash,
                entry_hash=entry_hash,
            )
            self.records.append(record)
            prev_hash = entry_hash

    def test_valid_chain_passes(self):
        """Test that a valid chain passes verification."""
        response = self.client.get("/api/v1/integrity/verify-chain/")
        assert response.status_code == 200
        assert response.data["status"] == "valid"
        assert response.data["count"] == 3

    def test_modifying_record_data_breaks_chain(self):
        """Test that modifying a record's data breaks the chain.

        This simulates an attacker modifying a record's data (e.g., changing
        consent_version or granted) without recomputing the hash.
        """
        # Modify the second record's data
        record = self.records[1]
        record.consent_version = "CT-marketing-v2"  # Tampered!
        # Save directly to DB, bypassing ORM guard
        ConsentRecord.objects.filter(id=record.id).update(consent_version="CT-marketing-v2")

        # Verify the chain
        response = self.client.get("/api/v1/integrity/verify-chain/")
        assert response.status_code == 409
        assert response.data["status"] == "invalid"
        assert "entry_hash mismatch" in response.data["errors"][0]

    def test_modifying_prev_hash_breaks_chain(self):
        """Test that modifying a record's prev_hash breaks the chain.

        This simulates an attacker trying to hide a modification by changing
        the prev_hash to match the tampered record.
        """
        # Modify the second record's prev_hash
        record = self.records[1]
        ConsentRecord.objects.filter(id=record.id).update(prev_hash="f" * 64)  # Tampered!

        # Verify the chain
        response = self.client.get("/api/v1/integrity/verify-chain/")
        assert response.status_code == 409
        assert response.data["status"] == "invalid"
        assert "prev_hash mismatch" in response.data["errors"][0]

    def test_deleting_record_breaks_chain(self):
        """Test that deleting a record breaks the chain.

        This simulates an attacker deleting a record to hide consent.
        """
        # Delete the second record
        # Note: This bypasses the ORM delete() guard by using QuerySet.delete()
        ConsentRecord.objects.filter(id=self.records[1].id).delete()

        # Verify the chain
        response = self.client.get("/api/v1/integrity/verify-chain/")
        assert response.status_code == 409
        assert response.data["status"] == "invalid"
        # The third record's prev_hash will not match the first record's entry_hash
        assert "prev_hash mismatch" in response.data["errors"][0]

    def test_inserting_record_in_middle_breaks_chain(self):
        """Test that inserting a record in the middle breaks the chain.

        This simulates an attacker inserting a fake record.
        """
        # Insert a fake record between the first and second records
        fake_timestamp = self.now + timedelta(minutes=1, seconds=30)
        ConsentRecord.objects.create(
            subject_id=self.subject_id,
            purpose=ConsentPurpose.MARKETING,
            consent_version="CT-marketing-v1",
            granted=False,
            timestamp=fake_timestamp,
            prev_hash=self.records[0].entry_hash,
            entry_hash="b" * 64,  # Fake hash
        )

        # Verify the chain
        response = self.client.get("/api/v1/integrity/verify-chain/")
        assert response.status_code == 409
        assert response.data["status"] == "invalid"
        # The second record's prev_hash will not match the fake record's entry_hash
        assert "prev_hash mismatch" in response.data["errors"][0]

    def test_reordering_records_breaks_chain(self):
        """Test that reordering records breaks the chain.

        This simulates an attacker reordering records to change the timeline.
        """
        # Swap the timestamps of the second and third records
        record2 = self.records[1]
        record3 = self.records[2]
        ConsentRecord.objects.filter(id=record2.id).update(timestamp=record3.timestamp)
        ConsentRecord.objects.filter(id=record3.id).update(timestamp=record2.timestamp)

        # Verify the chain
        response = self.client.get("/api/v1/integrity/verify-chain/")
        assert response.status_code == 409
        assert response.data["status"] == "invalid"
        # The prev_hash chain will be broken
        assert "prev_hash mismatch" in response.data["errors"][0]

    def test_empty_chain_passes(self):
        """Test that an empty chain passes verification."""
        # Delete all records
        ConsentRecord.objects.all().delete()

        # Verify the chain
        response = self.client.get("/api/v1/integrity/verify-chain/")
        assert response.status_code == 200
        assert response.data["status"] == "valid"
        assert response.data["count"] == 0
