from django.db import models
from stores.models import Store
from products.models import Product
from inventory.models import Inventory
from django.utils import timezone

class Sale(models.Model):
    store = models.ForeignKey(Store, related_name='sales', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='sales', on_delete=models.CASCADE)
    quantity = models.IntegerField()
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)  # Price per unit during the sale
    sale_date = models.DateTimeField(default=timezone.now)
    quantity_sold = models.IntegerField()
    
    def process_sale(store, product, quantity_sold):
    # Check if the store has enough stock and follow FIFO
        store_inventory = Inventory.objects.filter(warehouse=store.warehouse, product=product).order_by('lot__purchase_date')

        quantity_left = quantity_sold
        total_cost = 0
        expired_lots = []

        for inventory in store_inventory:
            if quantity_left <= 0:
                break

            # Skip expired lots
            if inventory.lot.purchase_date and inventory.lot.purchase_date < timezone.now().date():
                expired_lots.append(inventory.lot)
                continue

            # If this lot has enough stock
            if inventory.quantity <= quantity_left:
                quantity_left -= inventory.quantity
                total_cost += inventory.lot.purchase_price * inventory.quantity
                inventory.deduct_quantity(inventory.quantity)
            else:
                inventory.deduct_quantity(quantity_left)
                total_cost += inventory.lot.purchase_price * quantity_left
                quantity_left = 0

        # If there are expired lots, handle them accordingly
        if expired_lots:
            for lot in expired_lots:
                print(f"Lot {lot.id} of product {product.name} is expired and was skipped in the sale.")

        # Check if there's still stock left to fulfill the sale
        if quantity_left > 0:
            return f"Not enough stock to process the sale. Only {quantity_sold - quantity_left} sold."

        # Sale processed successfully, record the sale
        sale = Sale.objects.create(
            store=store,
            product=product,
            quantity=quantity_sold,
            sale_price=total_cost / quantity_sold if quantity_sold > 0 else 0  # Average sale price per unit based on FIFO cost
        )

        return f"Sale processed: {quantity_sold} {product.name} sold at {store.name}. Total cost: {total_cost}. Sale ID: {sale.id}"
    def __str__(self):
        return f"Sale at {self.store.name} on {self.date}"


class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, related_name="sale_details", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} sold in sale {self.sale.id}"
