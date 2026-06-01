from rest_framework import serializers

from .models import (
    ComplianceAlert,
    ComplianceRiskProfile,
    ComplianceAnalysisRun
)


class ComplianceAlertSerializer(serializers.ModelSerializer):

    class Meta:
        model = ComplianceAlert
        fields = '__all__'


class ComplianceRiskProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = ComplianceRiskProfile
        fields = '__all__'


class ComplianceAnalysisRunSerializer(serializers.ModelSerializer):

    class Meta:
        model = ComplianceAnalysisRun
        fields = '__all__'