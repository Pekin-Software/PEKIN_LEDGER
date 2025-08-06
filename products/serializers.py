from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.utils.timezone import now
from django.db import transaction
from django.db.models import Sum
from .models import Product, VariantAttribute, Category, ProductLot, ProductVariant
from inventory.models import Warehouse, Inventory, Section


class CategorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name']


class VariantAttributeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = VariantAttribute
        fields = ['id', 'name', 'value']

    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("Attribute name cannot be empty.")
        return value

class ProductLotSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProductLot
        fields = [
            'id', 'lot_number', 'quantity', 'purchase_date',
            'wholesale_quantity', 'purchase_price', 'wholesale_selling_price',
            'retail_selling_price', 'expired_date'
        ]

    def validate_quantity(self, value):
        if value < 0:
            raise ValidationError("Quantity cannot be negative.")
        return value

    def validate_expired_date(self, value):
        if value and value < now().date():
            raise ValidationError("Expired date cannot be in the past.")
        return value

    def _sync_inventory(self, instance, quantity_diff):
        """Ensure inventory is updated when lot quantities change."""
        product = instance.variant.product
        tenant = product.tenant

        warehouse = Warehouse.objects.filter(tenant=tenant, warehouse_type='general').first()
        if not warehouse:
            raise ValidationError("No general warehouse found for this tenant.")

        section = warehouse.sections.first() or Section.objects.create(warehouse=warehouse, name="Default Section")

        inventory, created = Inventory.objects.get_or_create(
            product=product,
            product_variant=instance.variant, 
            warehouse=warehouse,
            section=section,
            lot=instance,
            defaults={'tenant': tenant, 'quantity': instance.quantity}
        )

        if not created:
            new_quantity = inventory.quantity + quantity_diff
            if new_quantity < 0:
                raise ValidationError({
                    "quantity": f"Cannot reduce quantity below zero (result would be {new_quantity})."
                })
            inventory.quantity = new_quantity
            inventory.save()


    def _check_distribution_status(self, instance):
        """
        Ensure the lot has not been distributed to non-general warehouses.
        If it has, block the update.
        """
        distributed_exists = Inventory.objects.filter(
            product_variant=instance.variant,
            warehouse__tenant=instance.variant.product.tenant
        ).exclude(warehouse__warehouse_type='general').exists()

        if distributed_exists:
            raise ValidationError({
                "quantity": "Can not perform update. This batch has been distributed to other store."
            })

    @transaction.atomic
    def update(self, instance, validated_data):
        # Check if this lot has been distributed to non-general warehouses
        self._check_distribution_status(instance)

        old_quantity = instance.quantity
        new_quantity = validated_data.get('quantity', old_quantity)
        quantity_diff = new_quantity - old_quantity

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if quantity_diff != 0:
            self._sync_inventory(instance, quantity_diff)
        return instance


    @transaction.atomic
    def create(self, validated_data):
        instance = ProductLot.objects.create(**validated_data)
        self._sync_inventory(instance, instance.quantity)  # Sync inventory on create
        return instance

class ProductVariantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    attributes = VariantAttributeSerializer(many=True, required=False)
    lots = ProductLotSerializer(many=True)

    class Meta:
        model = ProductVariant
        fields = ['id', 'sku', 'barcode', 'barcode_image', 'attributes', 'lots']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('partial', False):
            for field in self.fields.values():
                field.required = False

    def validate(self, data):
        attrs = data.get('attributes', [])
        names = [a['name'].strip().lower() for a in attrs]
        if len(names) != len(set(names)):
            raise ValidationError({"attributes": "Duplicate attribute names are not allowed for a variant."})
        return data
    
    # def get_lots(self, variant):
    #     # Get inventory from context
    #     inventory_qs = self.context.get('inventory_qs')
    #     if not inventory_qs:
    #         return []

    #     # Get inventory rows for this variant
    #     variant_inventories = inventory_qs.filter(product_variant=variant)

    #     lots_data = []
    #     for inv in variant_inventories:
    #         lot_data = ProductLotSerializer(inv.lot).data  # serialize the lot
    #         lot_data['quantity'] = inv.quantity  # overwrite with inventory quantity
    #         lots_data.append(lot_data)
    #     return lots_data


    @transaction.atomic
    def update(self, instance, validated_data):
        attributes_data = validated_data.pop('attributes', [])
        lots_data = validated_data.pop('lots', [])

        # Update variant fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Sync attributes
        for attr_data in attributes_data:
            attr_id = attr_data.get('id')
            if attr_id:
                attr_instance = VariantAttribute.objects.get(id=attr_id, variant=instance)
                for key, val in attr_data.items():
                    setattr(attr_instance, key, val)
                attr_instance.save()
            else:
                VariantAttribute.objects.create(variant=instance, **attr_data)

        # Sync lots
        for lot_data in lots_data:
            lot_id = lot_data.get('id')
            if lot_id:
                lot_instance = ProductLot.objects.get(id=lot_id, variant=instance)
                ProductLotSerializer().update(lot_instance, lot_data)
            else:
                lot_data['variant'] = instance
                ProductLotSerializer().create(lot_data)

        return instance

class ProductSerializer(serializers.ModelSerializer):
    variants = ProductVariantSerializer(many=True, required=False)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), required=False)
    image_url = serializers.SerializerMethodField(read_only=True)
    lots = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'product_name', 'category', 'unit', 'threshold_value',
                   'currency',  'product_image', 'variants', 'image_url', 'lots' ]


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get('partial', False):  # <-- Detect partial updates
            for field in self.fields.values():
                field.required = False

    def get_lots(self, obj):
        sorted_lots = ProductLot.objects.filter(variant__product=obj).order_by('-expired_date')
        return ProductLotSerializer(sorted_lots, many=True).data

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.product_image:
            return request.build_absolute_uri(obj.product_image.url) if request else obj.product_image.url
        return None

    def validate_variants(self, variants):
        seen = set()
        for variant in variants:
            attrs = variant.get('attributes', [])
            # Normalize attribute tuples: sorted list of (name.lower(), value.lower())
            attr_tuple = tuple(sorted((attr['name'].strip().lower(), attr['value'].strip().lower()) for attr in attrs))
            if attr_tuple in seen:
                raise ValidationError("Duplicate product variant attributes detected within the same product.")
            seen.add(attr_tuple)
        return variants

    def validate(self, attrs):
        # Also validate variants for duplicates across the entire payload
        variants = attrs.get('variants', [])
        self.validate_variants(variants)
        return attrs
    
    def _product_variant_lot_exists(self, tenant, product_name, category, attributes_data, lot_data, exclude_product_id=None):
        products = Product.objects.filter(tenant=tenant, product_name__iexact=product_name, category=category)
        if exclude_product_id:
            products = products.exclude(id=exclude_product_id)

        new_attrs = {attr['name'].lower(): attr['value'].lower() for attr in attributes_data}

        for product in products:
            for variant in product.variants.all():
                existing_attrs = {attr.name.lower(): attr.value.lower() for attr in variant.attributes.all()}
                if existing_attrs == new_attrs:
                    # Match lot
                    lots = variant.lots.all()
                    if lot_data:
                        lots = lots.filter(
                            purchase_price=lot_data.get('purchase_price'),
                            retail_selling_price=lot_data.get('retail_selling_price'),
                            quantity=lot_data.get('quantity')
                        )
                    if lots.exists():
                        return True
        return False

    @transaction.atomic
    def create(self, validated_data):
        variants_data = validated_data.pop('variants', [])
    

        for variant_data in variants_data:
            attributes_data = variant_data.get('attributes', [])
            lots_data = variant_data.get('lots', [])
            for lot_data in lots_data:
                if self._product_variant_lot_exists(
            tenant=self.context['request'].tenant,
            product_name=validated_data['product_name'],
            category=validated_data['category'],
            attributes_data=attributes_data,
            lot_data=lot_data
        ):

                    raise ValidationError({"detail": "This product with the same variant and lot already exists."})

        # If passed all checks → create
        product = Product.objects.create(**validated_data)
        for variant_data in variants_data:
            attributes_data = variant_data.pop('attributes', [])
            lots_data = variant_data.pop('lots', [])
            variant = ProductVariant.objects.create(product=product, **variant_data)
            VariantAttribute.objects.bulk_create([VariantAttribute(variant=variant, **attr) for attr in attributes_data])
            for lot_data in lots_data:
                ProductLotSerializer().create({**lot_data, "variant": variant})
        return product


    # @transaction.atomic
    # def update(self, instance, validated_data):
    #     variants_data = validated_data.pop('variants', [])
    #     tenant = self.context['request'].tenant

    #     for variant_data in variants_data:
    #         attributes_data = variant_data.get('attributes', [])
    #         lots_data = variant_data.get('lots', [])
    #         for lot_data in lots_data:
    #             if self._product_variant_lot_exists(
    #                 tenant, validated_data.get('product_name', instance.product_name),
    #                 validated_data.get('category', instance.category),
    #                 attributes_data, lot_data,
    #                 exclude_product_id=instance.id
    #             ):
    #                 raise ValidationError({"detail": "This product with the same variant and lot already exists."})

    #     # Proceed with normal update
    #     for attr, value in validated_data.items():
    #         setattr(instance, attr, value)
    #     instance.save()

    #     for variant_data in variants_data:
    #         variant_id = variant_data.get('id')
    #         attributes_data = variant_data.pop('attributes', [])
    #         lots_data = variant_data.pop('lots', [])

    #         if variant_id:
    #             variant_instance = ProductVariant.objects.get(id=variant_id, product=instance)
    #             ProductVariantSerializer().update(variant_instance, {
    #                 **variant_data, "attributes": attributes_data, "lots": lots_data
    #             })
    #         else:
    #             variant = ProductVariant.objects.create(product=instance, **variant_data)
    #             VariantAttribute.objects.bulk_create([VariantAttribute(variant=variant, **attr) for attr in attributes_data])
    #             for lot_data in lots_data:
    #                 ProductLot.objects.create(variant=variant, **lot_data)
    #     return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        # --- Update basic product fields ---
        variants_data = validated_data.pop('variants', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # --- Update Variants ---
        if variants_data is not None:
            existing_variants = {v.id: v for v in instance.variants.all()}

            for variant_data in variants_data:
                variant_id = variant_data.get('id')
                lots_data = variant_data.pop('lots', None)

                if variant_id and variant_id in existing_variants:
                    variant_instance = existing_variants[variant_id]
                    # Partial update variant
                    for attr, value in variant_data.items():
                        setattr(variant_instance, attr, value)
                    variant_instance.save()
                else:
                    # Create new variant
                    variant_instance = ProductVariant.objects.create(product=instance, **variant_data)

                # --- Update Lots ---
                if lots_data is not None:
                    existing_lots = {lot.id: lot for lot in variant_instance.lots.all()}
                    lot_serializer = ProductLotSerializer()
                    for lot_data in lots_data:
                        lot_id = lot_data.get('id')
                        if lot_id and lot_id in existing_lots:
                            lot_instance = existing_lots[lot_id]
                            lot_serializer.update(lot_instance, lot_data)
                        else:
                            lot_serializer.create({**lot_data, "variant": variant_instance})

        return instance
    



