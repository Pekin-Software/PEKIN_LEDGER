# class StoreSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Store
#         fields = '__all__'

# class StoreProductSerializer(serializers.ModelSerializer):
#     stock_status = serializers.SerializerMethodField()

#     class Meta:
#         model = StoreProduct
#         fields = '__all__'

#     def get_stock_status(self, obj):
#         return obj.stock_status

from rest_framework import serializers
from .models import Store

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "store_name", "domain_name", "location"]
        read_only_fields = ["domain_name"]  # Prevents users from manually setting the domain
from rest_framework import serializers
from .models import Employee  # Assuming Employee model is in the same app

class EmployeeSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()  # This will display the string representation of the user model (i.e., the username)

    class Meta:
        model = Employee
        fields = ['user', 'position']  # Include position and user fields (user will automatically include user details like username)
