"""Management command to anonymize consent records past their retention TTL.

Implements the scheduled retention job described in ADR-0003. Finds all
withdrawn consent records whose retention period has expired and
anonymizes them (replaces subject_id with an unlinkable UUID, clears
ip_address and user_agent).

Usage:
    python manage.py anonymize_expired
    python manage.py anonymize_expired --dry-run
    python manage.py anonymize_expired --purpose marketing

Schedule this command via cron (daily at 03:00 UTC recommended):
    0 3 * * * cd /app && python manage.py anonymize_expired
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from django.core.management.base import BaseCommand

from consent_registry.models import ConsentPurpose
from consent_registry.retention import anonymize_expired, get_expired_records, get_retention_ttls

logger = structlog.get_logger(__name__)


class Command(BaseCommand):
    """Anonymize consent records past their retention TTL."""

    help = (
        "Anonymize withdrawn consent records whose retention period has expired. "
        "Replaces subject_id with an unlinkable UUID and clears ip_address/user_agent. "
        "Only withdrawn records (granted=False) are eligible. Active grants are retained."
    )

    def add_arguments(self, parser: Any) -> None:
        """Add command-line arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report how many records would be anonymized without making changes.",
        )
        parser.add_argument(
            "--purpose",
            type=str,
            choices=[p.value for p in ConsentPurpose],
            help="Limit anonymization to a specific purpose class.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        dry_run: bool = options["dry_run"]
        purpose_filter: str | None = options.get("purpose")
        now = datetime.now(UTC)

        ttls = get_retention_ttls()
        self.stdout.write(f"Retention TTLs (days): {ttls}")
        self.stdout.write(f"Reference time: {now.isoformat()}")

        expired = get_expired_records(now=now)

        if purpose_filter:
            expired = expired.filter(purpose=purpose_filter)

        count = expired.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: {count} record(s) would be anonymized.")
            )
            return

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No expired records to anonymize."))
            return

        anonymized = anonymize_expired(now=now, purpose=purpose_filter)
        self.stdout.write(self.style.SUCCESS(f"Anonymized {anonymized} record(s)."))
