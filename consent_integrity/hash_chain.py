"""Hash chain computation and verification.

This module provides functions to compute and verify the SHA-256 hash chain
for consent records. The chain provides tamper-evidence (ADR-0002).

Canonical serialization (ADR-0002):
- Field order: alphabetical by field name
- Encoding: UTF-8
- Null handling: explicit "null" string
- Example: {"consent_version":"CT-marketing-v1","granted":true,"prev_hash":"abc...","purpose":"marketing","subject_id":"uuid","timestamp":"2026-09-26T12:00:00Z"}
"""

import hashlib
import json
from typing import Any
from uuid import UUID


def canonical_serialize(record: dict[str, Any]) -> str:
    """Serialize a consent record to canonical form for hashing.

    Args:
        record: Dictionary representation of a consent record.

    Returns:
        Canonical JSON string (alphabetical keys, UTF-8, null="null").
    """
    # Convert UUIDs and datetimes to strings
    serialized = {}
    for key in sorted(record.keys()):
        value = record[key]
        if value is None:
            serialized[key] = "null"
        elif isinstance(value, UUID):
            serialized[key] = str(value)
        elif hasattr(value, "isoformat"):
            # datetime objects
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value

    return json.dumps(serialized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_entry_hash(record: dict[str, Any]) -> str:
    """Compute the SHA-256 entry hash for a consent record.

    Args:
        record: Dictionary representation of a consent record.

    Returns:
        SHA-256 hex digest (64 characters).
    """
    canonical = canonical_serialize(record)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_genesis_prev_hash() -> str:
    """Return the prev_hash for the genesis record (64 zeros)."""
    return "0" * 64
