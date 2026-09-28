"""Contract tests for ConsentRecord API.

These tests verify the API contract:
- POST /api/v1/consent-records/ — Grant or withdraw consent
- GET /api/v1/consent-records/ — Query consent records
- GET /api/v1/consent-records/<id>/ — Retrieve a specific consent record
- GET /api/v1/dsr/export/ — DSR export (Art. 15/20)
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

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
class TestConsentRecordAPI(TestCase):
    """Test the ConsentRecord API endpoints."""

    def setUp(self):
        """Set up test client and test data."""
        self.client = APIClient()
        self.subject_id = uuid.uuid4()
        self.now = datetime.now(UTC)

    def test_grant_consent(self):
        """Test granting consent via API."""
        data = {
            "subject_id": str(self.subject_id),
            "purpose": "marketing",
            "consent_version": "CT-marketing-v1",
            "granted": True,
            "ip_address": "127.0.0.1",
            "user_agent": "Test/1.0",
            "timestamp": self.now.isoformat(),
        }
        response = self.client.post("/api/v1/consent-records/", data, format="json")
        assert response.status_code == 201
        assert response.data["subject_id"] == str(self.subject_id)
        assert response.data["purpose"] == "marketing"
        assert response.data["granted"] is True
        assert "entry_hash" in response.data
        assert "prev_hash" in response.data

    def test_withdraw_consent(self):
        """Test withdrawing consent via API."""
        # First, grant consent
        grant_data = {
            "subject_id": str(self.subject_id),
            "purpose": "marketing",
            "consent_version": "CT-marketing-v1",
            "granted": True,
            "timestamp": self.now.isoformat(),
        }
        self.client.post("/api/v1/consent-records/", grant_data, format="json")

        # Then, withdraw consent
        withdraw_time = self.now + timedelta(minutes=1)
        withdraw_data = {
            "subject_id": str(self.subject_id),
            "purpose": "marketing",
            "consent_version": "CT-marketing-v1",
            "granted": False,
            "revoked_at": withdraw_time.isoformat(),
            "timestamp": withdraw_time.isoformat(),
        }
        response = self.client.post("/api/v1/consent-records/", withdraw_data, format="json")
        assert response.status_code == 201
        assert response.data["granted"] is False
        assert response.data["revoked_at"] is not None

    def test_query_consent_records(self):
        """Test querying consent records via API."""
        # Create a consent record
        ConsentRecord.objects.create(
            subject_id=self.subject_id,
            purpose=ConsentPurpose.MARKETING,
            consent_version="CT-marketing-v1",
            granted=True,
            timestamp=self.now,
            prev_hash="0" * 64,
            entry_hash="a" * 64,
        )

        # Query by subject_id
        response = self.client.get(f"/api/v1/consent-records/?subject_id={self.subject_id}")
        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["subject_id"] == str(self.subject_id)

    def test_retrieve_consent_record(self):
        """Test retrieving a specific consent record via API."""
        record = ConsentRecord.objects.create(
            subject_id=self.subject_id,
            purpose=ConsentPurpose.MARKETING,
            consent_version="CT-marketing-v1",
            granted=True,
            timestamp=self.now,
            prev_hash="0" * 64,
            entry_hash="a" * 64,
        )

        response = self.client.get(f"/api/v1/consent-records/{record.id}/")
        assert response.status_code == 200
        assert response.data["id"] == str(record.id)

    def test_dsr_export(self):
        """Test DSR export endpoint."""
        # Create multiple consent records for the same subject
        ConsentRecord.objects.create(
            subject_id=self.subject_id,
            purpose=ConsentPurpose.MARKETING,
            consent_version="CT-marketing-v1",
            granted=True,
            timestamp=self.now,
            prev_hash="0" * 64,
            entry_hash="a" * 64,
        )
        ConsentRecord.objects.create(
            subject_id=self.subject_id,
            purpose=ConsentPurpose.LOCATION,
            consent_version="CT-location-v1",
            granted=True,
            timestamp=self.now,
            prev_hash="a" * 64,
            entry_hash="b" * 64,
        )

        # Export all records for the subject
        response = self.client.get(f"/api/v1/dsr/export/?subject_id={self.subject_id}")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_reject_invalid_consent_version_format(self):
        """Test that invalid consent_version format is rejected."""
        data = {
            "subject_id": str(self.subject_id),
            "purpose": "marketing",
            "consent_version": "invalid-format",  # Does not match CT-<purpose>-v<N>
            "granted": True,
            "timestamp": self.now.isoformat(),
        }
        response = self.client.post("/api/v1/consent-records/", data, format="json")
        assert response.status_code == 400
        assert "consent_version" in response.data

    def test_reject_timestamp_outside_skew(self):
        """Test that timestamp outside ±5 minutes is rejected."""
        # Timestamp 10 minutes in the past
        past_time = self.now - timedelta(minutes=10)
        data = {
            "subject_id": str(self.subject_id),
            "purpose": "marketing",
            "consent_version": "CT-marketing-v1",
            "granted": True,
            "timestamp": past_time.isoformat(),
        }
        response = self.client.post("/api/v1/consent-records/", data, format="json")
        assert response.status_code == 400
        assert "timestamp" in response.data

    def test_reject_withdrawal_without_revoked_at(self):
        """Test that withdrawal (granted=False) requires revoked_at."""
        data = {
            "subject_id": str(self.subject_id),
            "purpose": "marketing",
            "consent_version": "CT-marketing-v1",
            "granted": False,
            "timestamp": self.now.isoformat(),
            # Missing revoked_at
        }
        response = self.client.post("/api/v1/consent-records/", data, format="json")
        assert response.status_code == 400
        assert "non_field_errors" in response.data

    def test_reject_grant_with_revoked_at(self):
        """Test that grant (granted=True) must not have revoked_at."""
        data = {
            "subject_id": str(self.subject_id),
            "purpose": "marketing",
            "consent_version": "CT-marketing-v1",
            "granted": True,
            "revoked_at": self.now.isoformat(),  # Should not be present
            "timestamp": self.now.isoformat(),
        }
        response = self.client.post("/api/v1/consent-records/", data, format="json")
        assert response.status_code == 400
        assert "non_field_errors" in response.data
