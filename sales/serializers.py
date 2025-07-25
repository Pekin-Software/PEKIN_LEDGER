from rest_framework import serializers
from .models import Sale, SaleDetail, ExchangeRate

class SaleDetailSerializer(serializers.ModelSerializer):
    lot_sku = serializers.CharField(source='lot.sku', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = SaleDetail
        fields = ['product_name', 'lot_sku', 'quantity_sold', 'price_at_sale', 'total', 'currency']

    def get_total(self, obj):
        return obj.quantity_sold * obj.price_at_sale
    
class SaleSerializer(serializers.ModelSerializer):
    sale_details = SaleDetailSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.store_name', read_only=True)
    sale_date = serializers.SerializerMethodField()
    cashier_id = serializers.SerializerMethodField()
    payment_method = serializers.CharField()

    
    class Meta:
        model = Sale
        fields = ['receipt_number', 'store_name', 'cashier_id', 'sale_date', 'sale_details', 'total_usd',
                 'total_lrd', 'currency', 'exchange_rate_used', 'grand_total',  'payment_method' ]
        read_only_fields = ['receipt_number', 'grand_total', 'sale_date', 'total_usd',
                 'total_lrd','store_name', 'cashier_id', 'sale_details', 'exchange_rate_used', 'currency']
    
    def get_sale_date(self, obj):
        # Format: July 23, 2025 @ 14:26:22
        return obj.sale_date.strftime("%B %d, %Y @ %H:%M:%S")
    
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
