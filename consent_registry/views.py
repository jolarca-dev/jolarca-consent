"""API views for ConsentRecord.

These views implement the consent registry API:
- POST /api/v1/consent-records/ — Grant or withdraw consent
- GET /api/v1/consent-records/ — Query consent records
- GET /api/v1/consent-records/<id>/ — Retrieve a specific consent record
- GET /api/v1/dsr/export/ — DSR export (Art. 15/20)
"""

from django.db.models import QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from consent_integrity.hash_chain import compute_entry_hash, get_genesis_prev_hash

from .models import ConsentRecord
from .serializers import ConsentRecordSerializer


class ConsentRecordViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet for ConsentRecord.

    Endpoints:
    - POST /api/v1/consent-records/ — Grant or withdraw consent
    - GET /api/v1/consent-records/ — Query consent records
    - GET /api/v1/consent-records/<id>/ — Retrieve a specific consent record
    """

    queryset = ConsentRecord.objects.all()
    serializer_class = ConsentRecordSerializer

    def get_queryset(self) -> QuerySet[ConsentRecord]:
        """Filter queryset based on query parameters.

        Returns:
            Filtered queryset.
        """
        queryset = super().get_queryset()

        # Apply filters from query parameters
        subject_id = self.request.query_params.get("subject_id")
        purpose = self.request.query_params.get("purpose")
        consent_version = self.request.query_params.get("consent_version")
        granted = self.request.query_params.get("granted")

        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if purpose:
            queryset = queryset.filter(purpose=purpose)
        if consent_version:
            queryset = queryset.filter(consent_version=consent_version)
        if granted is not None:
            queryset = queryset.filter(granted=granted.lower() == "true")

        return queryset

    def create(self, request: Request, *args, **kwargs) -> Response:
        """Create a new consent record (grant or withdraw).

        Computes prev_hash and entry_hash before saving.

        Args:
            request: The HTTP request.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Response with the created record (201 Created).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get the most recent record to determine prev_hash
        latest_record = ConsentRecord.objects.order_by("-timestamp").first()
        prev_hash = latest_record.entry_hash if latest_record else get_genesis_prev_hash()

        # Prepare the record data for hashing
        record_data = {
            "subject_id": str(serializer.validated_data["subject_id"]),
            "purpose": serializer.validated_data["purpose"],
            "consent_version": serializer.validated_data["consent_version"],
            "granted": serializer.validated_data["granted"],
            "ip_address": (
                str(serializer.validated_data["ip_address"])
                if serializer.validated_data.get("ip_address")
                else None
            ),
            "user_agent": serializer.validated_data.get("user_agent", ""),
            "timestamp": serializer.validated_data["timestamp"].isoformat(),
            "revoked_at": (
                serializer.validated_data["revoked_at"].isoformat()
                if serializer.validated_data.get("revoked_at")
                else None
            ),
            "prev_hash": prev_hash,
        }

        # Compute entry_hash
        entry_hash = compute_entry_hash(record_data)

        # Create the record with prev_hash and entry_hash
        instance = serializer.save(prev_hash=prev_hash, entry_hash=entry_hash)

        # Return the serialized record
        output_serializer = self.get_serializer(instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class DSRExportView(viewsets.ViewSet):
    """DSR export endpoint (Art. 15/20).

    GET /api/v1/dsr/export/?subject_id=<uuid>
    Returns all consent records for a subject.
    """

    def list(self, request: Request) -> Response:
        """Export all consent records for a subject.

        Args:
            request: The HTTP request.

        Returns:
            Response with all consent records for the subject.
        """
        subject_id = request.query_params.get("subject_id")
        if not subject_id:
            return Response(
                {"error": "subject_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        records = ConsentRecord.objects.filter(subject_id=subject_id).order_by("timestamp")
        serializer = ConsentRecordSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
