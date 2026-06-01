from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Account, JournalEntry
from .serializers import (
    AccountSerializer,
    JournalEntrySerializer
)

from .services import post_journal_entry

class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(
            tenant=self.request.user.tenant
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant
        )

class JournalEntryViewSet(viewsets.ModelViewSet):
    serializer_class = JournalEntrySerializer

    def get_queryset(self):
        return (
            JournalEntry.objects
            .filter(tenant=self.request.user.tenant)
            .prefetch_related("lines__account")
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant,
            created_by=self.request.user
        )