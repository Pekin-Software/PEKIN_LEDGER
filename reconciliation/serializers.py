from rest_framework import serializers

from .models import (
    CashTransaction,
    CashReconciliation,
    MobileMoneyTransaction,
    MobileMoneyReconciliation,
    SupplierVATTransaction,
    SupplierVATReconciliation,
    ReconciliationException
)


class CashTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashTransaction
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "store",
            "cashier",
            "is_reconciled",
            "cash_reconciliation",
        ]


class CashReconciliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashReconciliation
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "store",
            "system_cash_sales",
            "variance",
            "status",
            "reconciled_by",
            "reconciled_at",
        ]


class MobileMoneyTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileMoneyTransaction
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "store",
            "is_reconciled",
            "reconciled_at",
            "reconciled_by",
            "sale",
            "matched_amount",
            "remaining_amount",
            "is_partial_match",
        ]


class MobileMoneyReconciliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileMoneyReconciliation
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "store",
            "expected_amount",
            "actual_amount",
            "variance_amount",
            "status",
            "reconciled_by",
            "reconciled_at",
        ]


class SupplierVATTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierVATTransaction
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "store",
            "supplier",
            "is_reconciled",
        ]


class SupplierVATReconciliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplierVATReconciliation
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "store",
            "expected_vat_amount",
            "actual_vat_amount",
            "variance_amount",
            "status",
            "reconciled_by",
            "reconciled_at",
        ]


class ReconciliationExceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationException
        fields = "__all__"
        read_only_fields = [
            "tenant",
            "store",
        ]