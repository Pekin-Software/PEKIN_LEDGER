from rest_framework import serializers
from .models import Sale, SaleDetail, ExchangeRate, Payment, Refund, SaleCancellationLog

class SaleDetailSerializer(serializers.ModelSerializer):
    lot_sku = serializers.CharField(source='lot.sku', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    product_currency = serializers.CharField(source='product.currency', read_only=True)
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = SaleDetail
        fields = ['product_name', 'lot_sku', 'quantity_sold', 'price_at_sale', 'product_currency', 'total']

    def get_total(self, obj):
        return (obj.quantity_sold or 0) * (obj.price_at_sale or 0)

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'method', 'amount', 'currency', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        sale = data['sale']
        if sale.payment_status == 'Cancelled':
            raise serializers.ValidationError("Cannot make a payment to a cancelled sale.")
        return data

class SaleSerializer(serializers.ModelSerializer):
    sale_details = SaleDetailSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    payments = PaymentSerializer(many=True, read_only=True) 
    sale_date = serializers.SerializerMethodField()
    cashier_id = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['receipt_number', 'store_name', 'cashier_id', 'sale_date', 'sale_details', 'total_usd',
                 'total_lrd', 'currency', 'exchange_rate_used', 'grand_total', 'payments', 'payment_status', 'amount_paid', 'balance_due']
        read_only_fields = ['receipt_number', 'grand_total', 'amount_paid', 'balance_due', 'sale_date', 'total_usd',
                 'total_lrd','store_name', 'cashier_id', 'sale_details', 'exchange_rate_used', 'payment_status']
    
    def get_sale_date(self, obj):
        # Format: July 23, 2025 @ 14:26:22
        return obj.sale_date.strftime("%B %d, %Y @ %H:%M:%S")  if obj.sale_date else None
    
    def get_cashier_id(self, obj):
        return obj.cashier.id if obj.cashier else None
    
class SaleReportFilterSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    currency = serializers.ChoiceField(choices=[('USD', 'USD'), ('LRD', 'LRD')], default='USD')
    cashier_id = serializers.IntegerField(required=False)
    payment_method = serializers.ChoiceField(
        choices=['Cash', 'Orange_Money', 'Mobile_Money', 'Visa_MasterCard'],
        required=False
    )

class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ['id', 'usd_rate', 'effective_date', 'created_at']
        read_only_fields = ['effective_date', 'created_at']

class RefundSerializer(serializers.ModelSerializer):
    processed_by_name = serializers.CharField(source='processed_by.username', read_only=True)

    class Meta:
        model = Refund
        fields = ['id', 'amount', 'processed_by', 'processed_by_name', 'processed_at', 'reason']
        read_only_fields = ['id', 'processed_by_name', 'processed_at']

class SaleCancellationLogSerializer(serializers.ModelSerializer):
    cancelled_by_name = serializers.CharField(source='cancelled_by.username', read_only=True)

    class Meta:
        model = SaleCancellationLog
        fields = ['id', 'cancelled_by', 'cancelled_by_name', 'reason', 'details', 'cancelled_at']
        read_only_fields = ['id', 'cancelled_by_name', 'cancelled_at']

