# @receiver(post_save, sender=Sale)
# def update_inventory_on_sale(sender, instance, created, **kwargs):
#     if created:
#         sale = instance
#         product = sale.product
#         quantity_sold = sale.quantity
#         store = sale.store
        
#         # Fetch inventory based on store, warehouse, section, and product
#         inventories = Inventory.objects.filter(store=store, product=product).order_by('section__name')
        
#         quantity_left = quantity_sold
#         for inventory in inventories:
#             if quantity_left <= 0:
#                 break

#             # Deduct stock from the inventory section
#             if inventory.quantity <= quantity_left:
#                 quantity_left -= inventory.quantity
#                 inventory.deduct_quantity(inventory.quantity)
#             else:
#                 inventory.deduct_quantity(quantity_left)
#                 quantity_left = 0

#         if quantity_left > 0:
#             print(f"Not enough stock in the warehouse to fulfill the sale for {product.name}.")
