"""Serializers for ConsentRecord API.

These serializers handle validation and serialization of consent records.
The ConsentRecordSerializer enforces schema-level validation:
- subject_id must be a valid UUID
- purpose must be in the approved taxonomy
- consent_version must match the format CT-<purpose>-v<N>
- timestamp must be within acceptable skew (±5 minutes)
"""

import re
from datetime import UTC, datetime, timedelta

from rest_framework import serializers

from .models import ConsentPurpose, ConsentRecord


class ConsentRecordSerializer(serializers.ModelSerializer):
    """Serializer for ConsentRecord.

    Validates:
    - subject_id is a valid UUID
    - purpose is in the approved taxonomy
    - consent_version matches CT-<purpose>-v<N> format
    - timestamp is within ±5 minutes of current time
    """

    subject_id = serializers.UUIDField()
    purpose = serializers.ChoiceField(choices=ConsentPurpose.choices)
    consent_version = serializers.CharField(max_length=64)
    granted = serializers.BooleanField()
    ip_address = serializers.IPAddressField(required=False, allow_null=True)
    user_agent = serializers.CharField(required=False, allow_blank=True, default="")
    timestamp = serializers.DateTimeField()
    revoked_at = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        """Model metadata."""

        model = ConsentRecord
        fields = [
            "id",
            "subject_id",
            "purpose",
            "consent_version",
            "granted",
            "ip_address",
            "user_agent",
            "timestamp",
            "revoked_at",
            "prev_hash",
            "entry_hash",
            "created_at",
            "anonymized_at",
        ]
        read_only_fields = ["id", "prev_hash", "entry_hash", "created_at", "anonymized_at"]

    def validate_consent_version(self, value: str) -> str:
        """Validate consent_version format: CT-<purpose>-v<N>.

        Args:
            value: The consent_version string.

        Returns:
            The validated consent_version.

        Raises:
            ValidationError: If the format is invalid.
        """
        pattern = r"^CT-[a-z]+-v\d+$"
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                f"consent_version must match format CT-<purpose>-v<N> (e.g., CT-marketing-v1). "
                f"Got: {value}"
            )
        return value

    def validate_timestamp(self, value: datetime) -> datetime:
        """Validate timestamp is within ±5 minutes of current time.

        Args:
            value: The timestamp datetime.

        Returns:
            The validated timestamp.

        Raises:
            ValidationError: If the timestamp is outside the acceptable skew.
        """
        now = datetime.now(UTC)
        skew = timedelta(minutes=5)
        if value < now - skew or value > now + skew:
            raise serializers.ValidationError(
                f"timestamp must be within ±5 minutes of current time. "
                f"Got: {value.isoformat()}, current time: {now.isoformat()}"
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """Cross-field validation.

        Args:
            attrs: Dictionary of field values.

        Returns:
            The validated attributes.

        Raises:
            ValidationError: If cross-field validation fails.
        """
        purpose = attrs.get("purpose")
        consent_version = attrs.get("consent_version")
        granted = attrs.get("granted")
        revoked_at = attrs.get("revoked_at")

        # If consent_version is provided, check that it matches the purpose
        if consent_version and purpose:
            # Extract purpose from consent_version (CT-<purpose>-v<N>)
            match = re.match(r"^CT-([a-z]+)-v\d+$", consent_version)
            if match:
                version_purpose = match.group(1)
                if version_purpose != purpose:
                    raise serializers.ValidationError(
                        f"consent_version purpose ({version_purpose}) does not match "
                        f"purpose field ({purpose})"
                    )

        # If granted=False, revoked_at should be set
        if granted is False and not revoked_at:
            raise serializers.ValidationError(
                "revoked_at must be set when granted=False (withdrawal record)"
            )

        # If granted=True, revoked_at should not be set
        if granted is True and revoked_at:
            raise serializers.ValidationError(
                "revoked_at must not be set when granted=True (grant record)"
            )

        return attrs

    def create(self, validated_data: dict) -> ConsentRecord:
        """Create a new ConsentRecord.

        This method is called by the view after validation. The view is responsible
        for computing prev_hash and entry_hash before calling save().

        Args:
            validated_data: Validated field values.

        Returns:
            The created ConsentRecord.
        """
        # prev_hash and entry_hash are set by the view before save()
        return ConsentRecord(**validated_data)


class ConsentQuerySerializer(serializers.Serializer):
    """Serializer for consent query parameters.

    Used for GET /api/v1/consent-records/ endpoint.
    """

    subject_id = serializers.UUIDField(required=False)
    purpose = serializers.ChoiceField(choices=ConsentPurpose.choices, required=False)
    consent_version = serializers.CharField(max_length=64, required=False)
    granted = serializers.BooleanField(required=False)
