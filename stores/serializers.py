from rest_framework import serializers
from .models import Store
from customers.models import Client  # Assuming tenant model is Client
from django.db import connection

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "store_name", "tenant", "address", "city", "country", "phone_number"]
        read_only_fields = ["tenant"]

    def create(self, validated_data):
        # Get current tenant from schema_name (assuming django-tenants or similar is used)
        schema_name = connection.schema_name
        try:
            tenant = Client.objects.get(schema_name=schema_name)
        except Client.DoesNotExist:
            raise serializers.ValidationError("Tenant not found for this request.")

        # Attach the tenant to the store before saving
        validated_data["tenant"] = tenant
        return super().create(validated_data)
        
from rest_framework import serializers
from .models import Employee  # Assuming Employee model is in the same app

class EmployeeSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    position = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ['user', 'position']

    def get_position(self, obj):
        return obj.user.position