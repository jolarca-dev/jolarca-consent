"""URL configuration for consent_integrity app."""

from django.urls import path

from .views import VerifyChainView

urlpatterns = [
    path("verify-chain/", VerifyChainView.as_view(), name="verify-chain"),
]
