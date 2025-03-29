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


# class Order(models.Model):
#     customer = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="orders")
#     created_at = models.DateTimeField(auto_now_add=True)
#     status = models.CharField(
#         max_length=20,
#         choices=[("Pending", "Pending"), ("Completed", "Completed"), ("Cancelled", "Cancelled")],
#         default="Pending",
#     )

#     def __str__(self):
#         return f"Order {self.id} - {self.customer}"

# class OrderItem(models.Model):
#     order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
#     product = models.ForeignKey(Product, on_delete=models.CASCADE)
#     quantity = models.PositiveIntegerField()

#     def __str__(self):
#         return f"{self.quantity} x {self.product.product_name} (Order {self.order.id})"

#     def save(self, *args, **kwargs):
#         """Auto-deduct stock from available lots when an order is placed."""
#         if not self.pk:  # Only deduct stock on the first save (avoid double deduction)
#             self.deduct_stock()
#         super().save(*args, **kwargs)

#     def deduct_stock(self):
#         """Deduct stock from the oldest available lots (FIFO system)."""
#         remaining_qty = self.quantity
#         available_lots = (
#             self.product.lots.filter(quantity__gt=0, expired_date__gte=timezone.now()).order_by("purchase_date")
#         )

#         for lot in available_lots:
#             if remaining_qty <= 0:
#                 break

#             if lot.quantity >= remaining_qty:
#                 lot.quantity -= remaining_qty
#                 remaining_qty = 0
#             else:
#                 remaining_qty -= lot.quantity
#                 lot.quantity = 0

#             lot.save()  # Save the updated lot quantity

#         if remaining_qty > 0:
#             raise ValueError(f"Not enough stock available for {self.product.product_name}. Order cannot be completed.")

# def delete(self, *args, **kwargs):
#     """Restore stock to lots when an order item is deleted (order canceled)."""
#     returned_qty = self.quantity
#     used_lots = self.product.lots.filter(quantity__lt=F("initial_quantity")).order_by("-purchase_date")

#     for lot in used_lots:
#         if returned_qty <= 0:
#             break

#         space_left = lot.initial_quantity - lot.quantity
#         if space_left >= returned_qty:
#             lot.quantity += returned_qty
#             returned_qty = 0
#         else:
#             returned_qty -= space_left
#             lot.quantity = lot.initial_quantity

#         lot.save()

#     super().delete(*args, **kwargs)

