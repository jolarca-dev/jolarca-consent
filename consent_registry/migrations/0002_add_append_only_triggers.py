"""DB-level append-only enforcement.

This migration adds database triggers to prevent UPDATE and DELETE on the
consent_registry_consentrecord table. This enforces append-only at the DB level,
complementing the ORM-level enforcement in the model.

Why DB-level enforcement:
- ORM-only is insufficient: QuerySet.update(), bulk_create(), and raw SQL bypass save()
- DB-level triggers prevent ALL modification paths, including direct DB access
- This satisfies GDPR Art. 7(1) demonstrability and ISO 27001 A.8.12 integrity
"""

from django.db import connection, migrations


def add_triggers_postgres(apps, schema_editor):
    """Add triggers for PostgreSQL."""
    if connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        # Prevent UPDATE
        cursor.execute("""
            CREATE OR REPLACE FUNCTION prevent_consent_update()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'ConsentRecord is append-only; UPDATE is not allowed';
            END;
            $$ LANGUAGE plpgsql;
        """)
        cursor.execute("""
            CREATE TRIGGER prevent_consent_update_trigger
            BEFORE UPDATE ON consent_registry_consentrecord
            FOR EACH ROW
            EXECUTE FUNCTION prevent_consent_update();
        """)

        # Prevent DELETE
        cursor.execute("""
            CREATE OR REPLACE FUNCTION prevent_consent_delete()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'ConsentRecord cannot be deleted (ADR-0003: anonymize-don''t-delete)';
            END;
            $$ LANGUAGE plpgsql;
        """)
        cursor.execute("""
            CREATE TRIGGER prevent_consent_delete_trigger
            BEFORE DELETE ON consent_registry_consentrecord
            FOR EACH ROW
            EXECUTE FUNCTION prevent_consent_delete();
        """)


def remove_triggers_postgres(apps, schema_editor):
    """Remove triggers for PostgreSQL."""
    if connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TRIGGER IF EXISTS prevent_consent_delete_trigger ON consent_registry_consentrecord;")
        cursor.execute("DROP FUNCTION IF EXISTS prevent_consent_delete();")
        cursor.execute("DROP TRIGGER IF EXISTS prevent_consent_update_trigger ON consent_registry_consentrecord;")
        cursor.execute("DROP FUNCTION IF EXISTS prevent_consent_update();")


class Migration(migrations.Migration):
    """Add DB-level append-only triggers."""

    dependencies = [
        ("consent_registry", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_triggers_postgres, remove_triggers_postgres),
    ]
