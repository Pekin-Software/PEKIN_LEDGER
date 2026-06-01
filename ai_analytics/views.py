from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from customers.models import Client
from .services import AIAnalyticsService

from .models import (
    ComplianceAlert,
    ComplianceRiskProfile,
    ComplianceAnalysisRun
)

from .serializers import (
    ComplianceAlertSerializer,
    ComplianceRiskProfileSerializer,
    ComplianceAnalysisRunSerializer
)



class ComplianceAlertViewSet(viewsets.ModelViewSet):

    serializer_class = ComplianceAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ComplianceAlert.objects.filter(
            business_name=self.request.user.client
        ).order_by('-created_at')

    @action(
        detail=True,
        methods=['post'],
        url_path='resolve'
    )
    def resolve(self, request, pk=None):

        alert = self.get_object()

        alert.resolve(
            user=request.user
        )

        return Response(
            ComplianceAlertSerializer(alert).data
        )


class ComplianceRiskProfileViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ComplianceRiskProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ComplianceRiskProfile.objects.filter(
            business_name=self.request.user.client
        ).order_by('-created_at')


class ComplianceAnalysisRunViewSet(viewsets.ReadOnlyModelViewSet):

    serializer_class = ComplianceAnalysisRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ComplianceAnalysisRun.objects.filter(
            business_name=self.request.user.client
        ).order_by('-created_at')


class ComplianceIntelligenceViewSet(viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        url_path='run-analysis'
    )
    def run_analysis(self, request):

        reporting_period = request.data.get(
            'reporting_period'
        )

        result = AIAnalyticsService.run_full_analysis(
            business_name=request.user.client,
            reporting_period=reporting_period
        )

        alerts_data = ComplianceAlertSerializer(
            result['alerts'],
            many=True
        ).data

        return Response({
            'analysis_run_id': result['analysis_run_id'],
            'risk_score': result['risk_score'],
            'risk_level': result['risk_level'],
            'total_alerts': result['total_alerts'],
            'alerts': alerts_data
        })