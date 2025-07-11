# Generated by Django 5.1.7 on 2025-06-23 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0003_discount_lot_alter_lot_product_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lot',
            name='retail_discount_price',
        ),
        migrations.RemoveField(
            model_name='lot',
            name='wholesale_discount_price',
        ),
        migrations.RemoveField(
            model_name='product',
            name='description',
        ),
        migrations.AddField(
            model_name='lot',
            name='wholesale_quantity',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.DeleteModel(
            name='Discount',
        ),
    ]
