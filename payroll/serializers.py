from rest_framework import serializers

from .models import (
    Employee,
    PAYETaxBracket,
    PayrollRun,
    PayrollItem
)


class EmployeeSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Employee
        fields = '__all__'


class PAYETaxBracketSerializer(serializers.ModelSerializer):

    class Meta:
        model = PAYETaxBracket
        fields = '__all__'


class PayrollItemSerializer(serializers.ModelSerializer):

    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = PayrollItem
        fields = '__all__'

    def get_employee_name(self, obj):
        return f"{obj.employee.user.first_name} {obj.employee.user.last_name}"


class PayrollRunSerializer(serializers.ModelSerializer):

    items = PayrollItemSerializer(many=True, read_only=True)

    class Meta:
        model = PayrollRun
        fields = '__all__'
        read_only_fields = (
            'created_by',
            'approved_by',
            'approved_at',
            'posted_by',
            'posted_at',
            'total_gross_salary',
            'total_paye',
            'total_net_salary',
            'status',
        )