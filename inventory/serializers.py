from rest_framework import serializers
from .models import (Warehouse, Section, Inventory, Transfer, StockRequest, Supplier,
    Purchase,
    PurchaseItem,
    InventoryMovement)
from products.models import Product, ProductVariant, ProductLot
from django.db import transaction
from django.db.models import Q
from products.serializers import ProductLotSerializer, ProductVariantSerializer, VariantAttributeSerializer
from django.utils import timezone
from datetime import timedelta
from inventory.services.purchase_posting import (
    PurchasePostingService
)


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['tenant', 'warehouse_id', 'name', 'location', 'warehouse_type', 'store']

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['warehouse', 'name', 'description', 'aisle_number', 'shelf_number']

class ProductNestedSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(read_only=True)
    product_image_url = serializers.SerializerMethodField()
    variants = serializers.SerializerMethodField()  # NEW: include variants filtered by warehouse

    class Meta:
        model = Inventory.product.field.related_model
        fields = [
            'id', 'product_name', 'unit', 'threshold_value', 'product_image_url',
            'category', 'currency', 'variants'
        ]

    def get_product_image_url(self, obj):
        request = self.context.get('request')
        if obj.product_image:
            return request.build_absolute_uri(obj.product_image.url)
        return None

    # def get_variants(self, obj):
    #     """Return variants with lots filtered by the warehouse passed in context"""
    #     warehouse = self.context.get('warehouse')
    #     if not warehouse:
    #         return []

    #     variants = obj.variants.all()
    #     result = []
    #     today = timezone.now().date() 
    #     for variant in variants:
    #         # Get lots linked to this warehouse via Inventory
    #         inventory_qs = Inventory.objects.filter(product_variant=variant, warehouse=warehouse).select_related('lot')
    #         lots_data = []
    #         for inv in inventory_qs:
    #             if not inv.lot:
    #                 continue
    #             lots_data.append({
    #                 'id': inv.lot.id,
    #                 'lot_number': inv.lot.lot_number,
    #                 'quantity': inv.quantity,  # quantity in this warehouse
    #                 'purchase_date': inv.lot.purchase_date,
    #                 'wholesale_quantity': inv.lot.wholesale_quantity,
    #                 'purchase_price': inv.lot.purchase_price,
    #                 'wholesale_selling_price': inv.lot.wholesale_selling_price,
    #                 'retail_selling_price': inv.lot.retail_selling_price,
    #                 'expired_date': inv.lot.expired_date,
    #             })
    #         total_qty += inv.quantity
            
    #         if any(lot['expired_date'] and lot['expired_date'] < today for lot in lots_data):
    #             variant_status = "Expired"
    #         elif total_qty <= 0:
    #             variant_status = "Out of Stock"
    #         elif total_qty <= variant.product.threshold_value:
    #             variant_status = "Low Stock"
    #         else:
    #             variant_status = "In Stock"

    #         result.append({
    #             'id': variant.id,
    #             'sku': variant.sku,
    #             'barcode': variant.barcode,
    #             'barcode_image': variant.barcode_image.url if variant.barcode_image else None,
    #             'image_url': self.context.get('request').build_absolute_uri(variant.variant_image.url) if variant.variant_image else None,
    #             'attributes': VariantAttributeSerializer(variant.attributes.all(), many=True).data,
    #             'lots': lots_data,
    #             'stock_status': variant_status,
    #         })
    #     return result
    def get_variants(self, obj):
        """Return variants with lots filtered by the warehouse passed in context"""
        warehouse = self.context.get('warehouse')
        if not warehouse:
            return []

        variants = obj.variants.all()
        result = []
        today = timezone.now().date()  # <-- define it here

        for variant in variants:
            # Get lots linked to this warehouse via Inventory
            inventory_qs = Inventory.objects.filter(product_variant=variant, warehouse=warehouse).select_related('lot')
            lots_data = []
            total_qty = 0

            for inv in inventory_qs:
                if not inv.lot:
                    continue
                lots_data.append({
                    'id': inv.lot.id,
                    'lot_number': inv.lot.lot_number,
                    'quantity': inv.quantity,
                    'purchase_date': inv.lot.purchase_date,
                    'wholesale_quantity': inv.lot.wholesale_quantity,
                    'purchase_price': inv.lot.purchase_price,
                    'wholesale_selling_price': inv.lot.wholesale_selling_price,
                    'retail_selling_price': inv.lot.retail_selling_price,
                    'expired_date': inv.lot.expired_date,
                })
                total_qty += inv.quantity

            # Determine variant stock status
            if any(lot['expired_date'] and lot['expired_date'] < today for lot in lots_data):
                variant_status = "Expired"
            elif total_qty <= 0:
                variant_status = "Out of Stock"
            elif total_qty <= variant.product.threshold_value:
                variant_status = "Low Stock"
            else:
                variant_status = "In Stock"

            result.append({
                'id': variant.id,
                'sku': variant.sku,
                'barcode': variant.barcode,
                'barcode_image': variant.barcode_image.url if variant.barcode_image else None,
                'image_url': self.context.get('request').build_absolute_uri(variant.variant_image.url) if variant.variant_image else None,
                'attributes': VariantAttributeSerializer(variant.attributes.all(), many=True).data,
                'lots': lots_data,
                'stock_status': variant_status,
            })
        return result

class InventorySerializer(serializers.ModelSerializer):
    product = ProductNestedSerializer()
    stock_status = serializers.SerializerMethodField()
    total_quantity = serializers.SerializerMethodField()
    warehouse_type = serializers.CharField(source='warehouse.warehouse_type', read_only=True)
    overview = serializers.SerializerMethodField()

    class Meta:
        model = Inventory
        fields = [
            'id', 'product', 'stock_status', 'total_quantity', 'warehouse_type',
            'overview', 'added_at', 'updated_at'
        ]

    def to_representation(self, instance):
        self.fields['product'].context.update({'warehouse': instance.warehouse, 'request': self.context.get('request')})
        return super().to_representation(instance)

    def get_total_quantity(self, obj):
        return obj.quantity

    def get_stock_status(self, obj):
        if obj.quantity <= 0:
            return "Out of Stock"
        threshold = obj.product.threshold_value or 0
        if obj.quantity <= threshold:
            return "Low Stock"
        return "In Stock"
    
    @staticmethod
    def get_variants_warnings(inventories):
        today = timezone.now().date()
        low_stock_flag = False
        out_of_stock_flag = False
        expired_flag = False

        for inv in inventories:
            variant = inv.product_variant
            lots = variant.lots.all()  # You can filter by warehouse if needed

            if any(lot.expired_date and lot.expired_date < today for lot in lots):
                expired_flag = True

            qty = inv.quantity
            threshold = inv.product.threshold_value or 0

            if qty <= 0:
                out_of_stock_flag = True
            elif qty <= threshold:
                low_stock_flag = True

        warnings = []
        if expired_flag:
            warnings.append("Some variants have expired")
        if out_of_stock_flag:
            warnings.append("Some variants are out of stock")
        if low_stock_flag:
            warnings.append("Some variants are running low")

        return warnings
    
    # def get_overview(self, obj):
    #     if self.context.get('include_overview', False):
    #         inventories = self.context.get('all_inventories', [])
    #         today = timezone.now().date()

    #         store_inventories = [inv for inv in inventories if inv.warehouse.warehouse_type != "general"]
    #         general_inventories = [inv for inv in inventories if inv.warehouse.warehouse_type == "general"]

    #         def calculate_stats(inventories_subset):
    #             total_products = len(set(inv.product.id for inv in inventories_subset))
    #             in_stock = sum(1 for inv in inventories_subset if inv.quantity > (inv.product.threshold_value or 0))
    #             low_stock = sum(1 for inv in inventories_subset if 0 < inv.quantity <= (inv.product.threshold_value or 0))
    #             out_of_stock = sum(1 for inv in inventories_subset if inv.quantity <= 0)
    #             expiring_soon = sum(
    #                 1 for inv in inventories_subset
    #                 for lot in inv.product_variant.lots.filter(warehouse=inv.warehouse)
    #                 if lot.expired_date and today < lot.expired_date <= today + timedelta(days=30)
    #             )
    #             return {
    #                 "total_products": total_products,
    #                 "in_stock": in_stock,
    #                 "low_stock": low_stock,
    #                 "out_of_stock": out_of_stock,
    #                 "expiring_soon": expiring_soon,
    #             }

    #         return {
    #             "store_inventory": calculate_stats(store_inventories),
    #             "general_inventory": calculate_stats(general_inventories),
    #         }
    #     return None

    @staticmethod
    def compute_overview(inventories):
        """Reusable method to compute store/general overview"""
        today = timezone.now().date()

        store_inventories = [inv for inv in inventories if inv.warehouse.warehouse_type != "general"]
        general_inventories = [inv for inv in inventories if inv.warehouse.warehouse_type == "general"]

        def calculate_stats(inventories_subset):
            total_products = len(set(inv.product.id for inv in inventories_subset))
            in_stock = sum(1 for inv in inventories_subset if inv.quantity > (inv.product.threshold_value or 0))
            low_stock = sum(1 for inv in inventories_subset if 0 < inv.quantity <= (inv.product.threshold_value or 0))
            out_of_stock = sum(1 for inv in inventories_subset if inv.quantity <= 0)
            expiring_soon = sum(
                1 for inv in inventories_subset
                for lot in inv.product_variant.lots.filter(warehouse=inv.warehouse)
                if lot.expired_date and today < lot.expired_date <= today + timedelta(days=30)
            )
            return {
                "total_products": total_products,
                "in_stock": in_stock,
                "low_stock": low_stock,
                "out_of_stock": out_of_stock,
                "expiring_soon": expiring_soon,
            }

        return {
            "store_inventory": calculate_stats(store_inventories),
            "general_inventory": calculate_stats(general_inventories),
        }

    def get_overview(self, obj):
        if self.context.get('include_overview', False):
            inventories = self.context.get('all_inventories', [])
            return self.compute_overview(inventories)
        return None


class AddInventoryListSerializer(serializers.ListSerializer):
    def create(self, validated_data_list):
        if not validated_data_list:
            return []

        # Assume all items have the same warehouse/store context
        store = validated_data_list[0]['store']
        tenant = store.tenant
        warehouse = validated_data_list[0]['warehouse']

        new_inventories = []
        inventories_to_update = []

        for data in validated_data_list:
            # --- Determine the lot to use ---
            if warehouse.warehouse_type == 'store':
                # Create a new independent lot for this store
                store_lot = ProductLot.objects.create(
                    variant=data['variant'],
                    warehouse=warehouse,
                    quantity=data['quantity'],
                    purchase_date=data['lot'].purchase_date,
                    purchase_price=data['lot'].purchase_price,
                    wholesale_quantity=data['lot'].wholesale_quantity,
                    wholesale_selling_price=data['lot'].wholesale_selling_price,
                    retail_selling_price=data['lot'].retail_selling_price,
                    expired_date=data['lot'].expired_date,
                )
                data['lot'] = store_lot  # make sure inventory points to the new store lot

            # --- Check if an inventory row already exists ---
            inventory_qs = Inventory.objects.filter(
                tenant=tenant,
                warehouse=warehouse,
                product=data['product'],
                product_variant=data['variant'],
                lot=data['lot'],
                section=data['section']
            )

            if inventory_qs.exists():
                inv = inventory_qs.first()
                inv.quantity += data['quantity']
                inventories_to_update.append(inv)
            else:
                new_inventories.append(Inventory(
                    tenant=tenant,
                    warehouse=warehouse,
                    section=data['section'],
                    product=data['product'],
                    product_variant=data['variant'],
                    lot=data['lot'],
                    quantity=data['quantity']
                ))

        # --- Save all inventories ---
        with transaction.atomic():
            if new_inventories:
                Inventory.objects.bulk_create(new_inventories)
            if inventories_to_update:
                Inventory.objects.bulk_update(inventories_to_update, ['quantity'])

        return new_inventories + inventories_to_update

#Main Inventory serializer to add product the use the helper
class AddInventorySerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField() 
    lot_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    section_id = serializers.IntegerField(required=False)

    class Meta:
        list_serializer_class = AddInventoryListSerializer

    def validate(self, data):
        store = self.context.get('store')
        warehouse = self.context.get('warehouse')
        if not store or not warehouse:
            raise serializers.ValidationError("Internal server error: store or warehouse context missing.")

        data['store'] = store
        data['warehouse'] = warehouse

        # Validate Product
        try:
            product = Product.objects.get(id=data['product_id'], tenant=store.tenant)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Product not found for this tenant.")
        data['product'] = product

        try:
            variant = product.variants.get(id=data['variant_id'])
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError("Variant does not belong to the product.")
        data['variant'] = variant

         # Validate Lot
        try:
            lot = ProductLot.objects.get(id=data['lot_id'])
        except ProductLot.DoesNotExist:
            raise serializers.ValidationError("Lot not found.")

        # Validate or assign Section
        section_id = data.get('section_id')
        if section_id:
            try:
                section = warehouse.sections.get(id=section_id)
            except Section.DoesNotExist:
                raise serializers.ValidationError("Section not found in warehouse.")
        else:
            section = warehouse.sections.first()
            if not section:
                section = Section.objects.create(
                    warehouse=warehouse,
                    name=f"{warehouse.name} - Default Section"
                )
        data['section'] = section

        return data

class TransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transfer
        fields = ['source_warehouse', 'destination_warehouse', 'product', 'quantity', 'transfer_date', 'status', 'confirmed_by']

class StockRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockRequest
        fields = ['store', 'warehouse_from', 'warehouse_to', 'product', 'quantity_requested', 'status', 'request_date']

class SupplierSerializer(
    serializers.ModelSerializer
):

    class Meta:
        model = Supplier
        fields = '__all__'


class PurchaseItemSerializer(
    serializers.ModelSerializer
):

    product_name = serializers.CharField(
        source='product.product_name',
        read_only=True
    )

    variant_sku = serializers.CharField(
        source='product_variant.sku',
        read_only=True
    )

    class Meta:
        model = PurchaseItem

        fields = [
            'id',
            'purchase',
            'product',
            'product_name',
            'product_variant',
            'variant_sku',
            'quantity',
            'unit_cost',
            'subtotal',
            'vat_rate',
            'vat_amount',
            'total'
        ]

        read_only_fields = [
            'subtotal',
            'vat_amount',
            'total'
        ]

class PurchaseSerializer(serializers.ModelSerializer):

    items = PurchaseItemSerializer(many=True)

    supplier_name = serializers.CharField(
        source="supplier.name",
        read_only=True
    )

    class Meta:
        model = Purchase

        fields = [
            "id",
            "tenant",
            "store_name",
            "supplier",
            "supplier_name",
            "invoice_number",
            "invoice_date",
            "subtotal",
            "vat_total",
            "grand_total",
            "status",
            "is_posted",
            "journal_entry_id",
            "created_at",
            "items",
        ]

        read_only_fields = [
            "tenant",
            "subtotal",
            "vat_total",
            "grand_total",
            "status",
            "is_posted",
            "journal_entry_id",
            "created_at",
        ]
class InventoryMovementSerializer(serializers.ModelSerializer):

    product_name = serializers.CharField(
        source="product.product_name",
        read_only=True
    )

    warehouse_name = serializers.CharField(
        source="warehouse.name",
        read_only=True
    )

    class Meta:
        model = InventoryMovement

        fields = [
            "id",
            "tenant",
            "warehouse",
            "warehouse_name",
            "product",
            "product_name",
            "product_variant",
            "lot",
            "purchase",
            "sale",
            "transfer",
            "movement_type",
            "quantity",
            "unit_cost",
            "total_cost",
            "reference",
            "remarks",
            "created_at",
        ]