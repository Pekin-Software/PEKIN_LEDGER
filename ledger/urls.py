from django.contrib import admin
from django.urls import path, include

from rest_framework.routers import DefaultRouter

from ledger.views import (
    AccountViewSet,
    JournalEntryViewSet
)

router = DefaultRouter()

router.register(r'accounts', AccountViewSet)
router.register(r'journal-entries', JournalEntryViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]