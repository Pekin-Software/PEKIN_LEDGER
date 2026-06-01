from rest_framework import serializers

from taxation.models import (
    TaxClass,
    TaxPeriod,
    VATLedger,
    StoreVATSummary,
    VATReturn,
    VATAdjustment,
    TaxPayment,
)


class TaxClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxClass
        fields = "__all__"
        read_only_fields = ["tenant", "created_at"]


class TaxPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxPeriod
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "created_by",
            "approved_by",
            "approved_at",
            "locked_by",
            "locked_at",
            "created_at",
        ]


class VATLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = VATLedger
        fields = "__all__"
        read_only_fields = ["tenant", "created_by", "created_at"]


class StoreVATSummarySerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="store.name", read_only=True)
    period = serializers.CharField(source="tax_period.period", read_only=True)

    class Meta:
        model = StoreVATSummary
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "output_vat",
            "input_vat",
            "adjustment_vat",
            "net_vat_payable",
            "submitted_by",
            "submitted_at",
            "reviewed_by",
            "reviewed_at",
            "created_at",
        ]


class VATReturnSerializer(serializers.ModelSerializer):
    period = serializers.CharField(source="tax_period.period", read_only=True)

    class Meta:
        model = VATReturn
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "total_output_vat",
            "total_input_vat",
            "total_adjustment_vat",
            "net_vat_payable",
            "carried_forward_credit",
            "approved_by",
            "approved_at",
            "filed_by",
            "filed_at",
            "created_at",
        ]


class VATAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VATAdjustment
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "created_by",
            "approved_by",
            "approved_at",
            "is_approved",
            "created_at",
        ]


class TaxPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxPayment
        fields = "__all__"
        read_only_fields = ["tenant", "paid_by", "paid_at", "created_at"]