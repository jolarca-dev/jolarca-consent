#!/usr/bin/env python3
"""Offline chain verifier — verify the integrity of the consent ledger.

This is a stdlib-only script that reads all consent records from the database,
recomputes the hash chain, and verifies that it is consistent.

Usage:
    python scripts/verify_chain.py [--database-url URL]

The script connects to the database using the provided URL or the DATABASE_URL
environment variable. If neither is provided, it defaults to:
    postgresql://jolarca_consent:localhost:5432/jolarca_consent

Exit codes:
    0 — chain is valid
    1 — chain is invalid (mismatch detected)
    2 — database connection error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
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


def verify_chain(database_url: str) -> int:
    """Verify the hash chain integrity.

    Args:
        database_url: PostgreSQL connection URL.

    Returns:
        0 if chain is valid, 1 if invalid, 2 if connection error.
    """
    try:
        import psycopg
    except ImportError:
        print("ERROR: psycopg is not installed. Install with: pip install psycopg[binary]")
        return 2

    try:
        with psycopg.connect(database_url) as conn, conn.cursor() as cursor:
            # Read all records in insertion order
            cursor.execute(
                """
                    SELECT id, subject_id, purpose, consent_version, granted,
                           ip_address, user_agent, timestamp, revoked_at,
                           prev_hash, entry_hash, anonymized_at
                    FROM consent_registry_consentrecord
                    ORDER BY timestamp, id
                    """
            )
            rows = cursor.fetchall()

            if not rows:
                print("OK: no records in chain (empty ledger)")
                return 0

            prev_entry_hash = get_genesis_prev_hash()
            errors = []

            for i, row in enumerate(rows):
                (
                    record_id,
                    subject_id,
                    purpose,
                    consent_version,
                    granted,
                    ip_address,
                    user_agent,
                    timestamp,
                    revoked_at,
                    stored_prev_hash,
                    stored_entry_hash,
                    anonymized_at,
                ) = row

                # Check prev_hash (applies to ALL records, including anonymized)
                if stored_prev_hash != prev_entry_hash:
                    errors.append(
                        f"Record {i} (id={record_id}): prev_hash mismatch. "
                        f"Expected {prev_entry_hash}, got {stored_prev_hash}"
                    )

                # For anonymized records, skip entry_hash recomputation.
                # The stored entry_hash was computed over the original data
                # before anonymization. The subject_id, ip_address, and
                # user_agent have been replaced/cleared, so recomputing
                # would produce a different hash. We trust the stored hash
                # for anonymized records but still verify chain continuity
                # via prev_hash (checked above).
                if anonymized_at is not None:
                    prev_entry_hash = stored_entry_hash
                    continue

                # Recompute entry_hash for non-anonymized records
                record_data = {
                    "subject_id": str(subject_id),
                    "purpose": purpose,
                    "consent_version": consent_version,
                    "granted": granted,
                    "ip_address": str(ip_address) if ip_address else None,
                    "user_agent": user_agent or "",
                    "timestamp": timestamp.isoformat(),
                    "revoked_at": revoked_at.isoformat() if revoked_at else None,
                    "prev_hash": stored_prev_hash,
                }
                computed_entry_hash = compute_entry_hash(record_data)

                # Check entry_hash
                if computed_entry_hash != stored_entry_hash:
                    errors.append(
                        f"Record {i} (id={record_id}): entry_hash mismatch. "
                        f"Expected {computed_entry_hash}, got {stored_entry_hash}"
                    )

                # Update prev_entry_hash for next iteration
                prev_entry_hash = stored_entry_hash

            if errors:
                print(f"FAILED: {len(errors)} error(s) detected:")
                for error in errors:
                    print(f"  - {error}")
                return 1

            print(f"OK: chain is valid ({len(rows)} records)")
            return 0

    except psycopg.OperationalError as e:
        print(f"ERROR: database connection failed: {e}")
        return 2
    except Exception as e:
        print(f"ERROR: unexpected error: {e}")
        return 2


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Verify the consent ledger hash chain")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (default: $DATABASE_URL or postgresql://localhost:5432/jolarca_consent)",
    )
    args = parser.parse_args()

    if not args.database_url:
        print("ERROR: --database-url or DATABASE_URL environment variable is required")
        return 2

    return verify_chain(args.database_url)


if __name__ == "__main__":
    sys.exit(main())
