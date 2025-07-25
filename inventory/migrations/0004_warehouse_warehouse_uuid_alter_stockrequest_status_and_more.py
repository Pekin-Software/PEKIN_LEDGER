# Generated by Django 5.1.7 on 2025-07-13 14:56

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
        ('inventory', '0003_initial'),
        ('products', '0004_remove_lot_retail_discount_price_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='warehouse',
            name='warehouse_uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
        migrations.AlterField(
            model_name='stockrequest',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='transfer',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed')], default='pending', max_length=20),
        ),
        migrations.AlterField(
            model_name='warehouse',
            name='warehouse_id',
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='inventory',
            unique_together={('warehouse', 'section', 'product', 'lot')},
        ),
        migrations.AddIndex(
            model_name='inventory',
            index=models.Index(fields=['product', 'warehouse'], name='inventory_i_product_f6b65e_idx'),
        ),
    ]
