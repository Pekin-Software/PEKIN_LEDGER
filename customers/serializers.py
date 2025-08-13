from rest_framework import serializers
from .models import Client, Domain, User

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'  # This will include all fields of the Client model

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = '__all__'  # Includes all fields of Domain
class UserSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(write_only=True, required=False)  # Only needed for admins

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'first_name', 'middle_name', 'last_name', 'phone1', 'phone2', 
                  'photo', 'address', 'city', 'country', 'date_of_birth', 'nationality', 'position', 'business_name']
    
    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
    # Check if we are creating an admin account
        business_name = validated_data.pop('business_name', None)
        password = validated_data.pop('password')  # Handle password manually

        if business_name:
            # Main account (Admin)
            user = User.objects.create_user(business_name=business_name, password=password, **validated_data)
        else:
            # Subaccount: get domain from request context
            domain = self.context['request'].user.domain
            user = User.objects.create(domain=domain, **validated_data)
            user.set_password(password)
            user.save()

        return user

class StaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "address",
            "city",
            "phone1",
            "phone2",
            "email",
            "position",
        ]

