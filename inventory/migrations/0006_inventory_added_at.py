# Generated by Django 5.1.7 on 2025-07-13 16:42

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_alter_warehouse_warehouse_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventory',
            name='added_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
