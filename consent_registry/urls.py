"""URL configuration for consent_registry app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ConsentRecordViewSet, DSRExportView

router = DefaultRouter()
router.register(r"consent-records", ConsentRecordViewSet, basename="consentrecord")
router.register(r"dsr/export", DSRExportView, basename="dsr-export")

urlpatterns = [
    path("", include(router.urls)),
]
