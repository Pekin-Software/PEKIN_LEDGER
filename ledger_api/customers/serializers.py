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
    business_name = serializers.CharField(write_only=True)  # Only needed at signup

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'first_name', 'middle_name', 'last_name', 'phone1', 'phone2', 'photo', 'address', 'city', 'country', 'date_of_birth', 'nationality', 'position', 'business_name']
    
    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        business_name = validated_data.pop('business_name')  # Extract business name
        return User.objects.create_user(business_name=business_name, **validated_data)
