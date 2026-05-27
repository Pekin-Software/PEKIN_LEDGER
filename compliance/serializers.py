from rest_framework import serializers

from .models import (
    EInvoice,
    EInvoiceLine,
    TaxFiling,
    PeriodLock,
    ComplianceAuditLog,
    POSComplianceEvent,
    InventoryComplianceEvent,
    BranchVATSummary,
)


class EInvoiceLineSerializer(serializers.ModelSerializer):

    class Meta:
        model = EInvoiceLine
        fields = "__all__"


class EInvoiceSerializer(serializers.ModelSerializer):

    lines = EInvoiceLineSerializer(many=True, read_only=True)

    class Meta:
        model = EInvoice
        fields = "__all__"
        read_only_fields = [
            "qr_code_payload",
            "digital_signature",
            "issued_at",
            "created_by",
            "created_at",
        ]


class TaxFilingSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaxFiling
        fields = "__all__"
        read_only_fields = [
            "lra_reference",
            "submitted_at",
            "approved_by",
            "approved_at",
            "created_at",
        ]


class PeriodLockSerializer(serializers.ModelSerializer):

    class Meta:
        model = PeriodLock
        fields = "__all__"
        read_only_fields = [
            "locked_by",
            "locked_at",
        ]


class ComplianceAuditLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = ComplianceAuditLog
        fields = "__all__"
        read_only_fields = [
            "created_at",
        ]


class POSComplianceEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = POSComplianceEvent
        fields = "__all__"
        read_only_fields = [
            "created_at",
        ]


class InventoryComplianceEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = InventoryComplianceEvent
        fields = "__all__"
        read_only_fields = [
            "created_at",
        ]


class BranchVATSummarySerializer(serializers.ModelSerializer):

    class Meta:
        model = BranchVATSummary
        fields = "__all__"
        read_only_fields = [
            "generated_at",
        ]