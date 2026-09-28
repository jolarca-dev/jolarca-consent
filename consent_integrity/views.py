"""Chain verification API endpoint.

This endpoint verifies the hash chain integrity on-demand.
"""

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from consent_registry.models import ConsentRecord

from .hash_chain import compute_entry_hash, get_genesis_prev_hash


class VerifyChainView(APIView):
    """Verify the hash chain integrity.

    GET /api/v1/integrity/verify-chain/
    Returns 200 OK if chain is valid, 409 Conflict if any mismatch.
    """

    def get(self, request: Request) -> Response:
        """Verify the hash chain.

        Args:
            request: The HTTP request.

        Returns:
            Response with verification result.
        """
        # Read all records in insertion order
        records = ConsentRecord.objects.order_by("timestamp", "id")

        if not records.exists():
            return Response(
                {"status": "valid", "message": "No records in chain (empty ledger)", "count": 0},
                status=status.HTTP_200_OK,
            )

        prev_entry_hash = get_genesis_prev_hash()
        errors = []

        for i, record in enumerate(records):
            # Check prev_hash
            if record.prev_hash != prev_entry_hash:
                errors.append(
                    f"Record {i} (id={record.id}): prev_hash mismatch. "
                    f"Expected {prev_entry_hash}, got {record.prev_hash}"
                )

            # Recompute entry_hash
            record_data = {
                "subject_id": str(record.subject_id),
                "purpose": record.purpose,
                "consent_version": record.consent_version,
                "granted": record.granted,
                "ip_address": str(record.ip_address) if record.ip_address else None,
                "user_agent": record.user_agent or "",
                "timestamp": record.timestamp.isoformat(),
                "revoked_at": record.revoked_at.isoformat() if record.revoked_at else None,
                "prev_hash": record.prev_hash,
            }
            computed_entry_hash = compute_entry_hash(record_data)

            # Check entry_hash
            if computed_entry_hash != record.entry_hash:
                errors.append(
                    f"Record {i} (id={record.id}): entry_hash mismatch. "
                    f"Expected {computed_entry_hash}, got {record.entry_hash}"
                )

            # Update prev_entry_hash for next iteration
            prev_entry_hash = record.entry_hash

        if errors:
            return Response(
                {
                    "status": "invalid",
                    "message": f"{len(errors)} error(s) detected",
                    "errors": errors,
                    "count": records.count(),
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "status": "valid",
                "message": "Chain is valid",
                "count": records.count(),
            },
            status=status.HTTP_200_OK,
        )
