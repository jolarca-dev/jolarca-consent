"""consent_registry Django app configuration."""

from django.apps import AppConfig


class ConsentRegistryConfig(AppConfig):
    """Configuration for the consent_registry app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "consent_registry"
    verbose_name = "Consent Registry"
