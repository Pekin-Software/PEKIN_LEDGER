from decimal import Decimal

from django.db.models import Sum, Count
from django.utils import timezone

from taxation.models import VATLedger
from sales.models import Sale

from compliance.models import (
    TaxFiling,
    ComplianceAlert,
    ComplianceRiskProfile,
    ComplianceAnalysisRun
)


class ComplianceIntelligenceService:

    @staticmethod
    def get_risk_level(score):

        if score >= 80:
            return 'CRITICAL'

        if score >= 60:
            return 'HIGH'

        if score >= 35:
            return 'MEDIUM'

        return 'LOW'

    @staticmethod
    def create_alert(
        organization,
        alert_type,
        severity,
        title,
        message,
        reference=None
    ):

        return ComplianceAlert.objects.create(
            organization=organization,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            reference=reference
        )

    @staticmethod
    def analyze_vat_anomalies(
        organization,
        reporting_period
    ):

        alerts = []

        vat_entries = VATLedger.objects.filter(
            organization=organization,
            reporting_period=reporting_period
        )

        output_vat = vat_entries.filter(
            vat_type='OUTPUT'
        ).aggregate(
            total=Sum('vat_amount')
        )['total'] or Decimal('0.00')

        input_vat = vat_entries.filter(
            vat_type='INPUT'
        ).aggregate(
            total=Sum('vat_amount')
        )['total'] or Decimal('0.00')

        if output_vat == 0:
            alerts.append(
                ComplianceIntelligenceService.create_alert(
                    organization=organization,
                    alert_type='VAT_ANOMALY',
                    severity='HIGH',
                    title='No Output VAT Recorded',
                    message='No output VAT was recorded for this reporting period.',
                    reference=reporting_period
                )
            )

        if input_vat > output_vat:
            alerts.append(
                ComplianceIntelligenceService.create_alert(
                    organization=organization,
                    alert_type='VAT_ANOMALY',
                    severity='HIGH',
                    title='Input VAT Exceeds Output VAT',
                    message='Input VAT is greater than output VAT. Review supplier VAT claims.',
                    reference=reporting_period
                )
            )

        if output_vat > 0:
            input_ratio = (input_vat / output_vat) * Decimal('100')

            if input_ratio > Decimal('80'):
                alerts.append(
                    ComplianceIntelligenceService.create_alert(
                        organization=organization,
                        alert_type='VAT_ANOMALY',
                        severity='MEDIUM',
                        title='High Input VAT Ratio',
                        message='Input VAT is unusually high compared to output VAT.',
                        reference=reporting_period
                    )
                )

        return alerts

    @staticmethod
    def analyze_refund_risk(
        organization,
        reporting_period
    ):

        alerts = []

        filing = TaxFiling.objects.filter(
            organization=organization,
            tax_type='VAT',
            reporting_period=reporting_period
        ).first()

        if not filing:
            return alerts

        if filing.net_tax_payable < 0:
            alerts.append(
                ComplianceIntelligenceService.create_alert(
                    organization=organization,
                    alert_type='REFUND_RISK',
                    severity='HIGH',
                    title='VAT Refund Position Detected',
                    message='This VAT filing shows a refund position. Review supporting input VAT documentation.',
                    reference=reporting_period
                )
            )

        return alerts

    @staticmethod
    def analyze_sales_patterns(
        organization,
        reporting_period=None
    ):

        alerts = []

        sales = Sale.objects.filter(
            organization=organization
        )

        if reporting_period:
            sales = sales.filter(
                created_at__strftime='%Y-%m'
            )

        sale_count = sales.count()

        total_sales = sales.aggregate(
            total=Sum('grand_total')
        )['total'] or Decimal('0.00')

        if sale_count == 0:
            alerts.append(
                ComplianceIntelligenceService.create_alert(
                    organization=organization,
                    alert_type='SALES_PATTERN',
                    severity='MEDIUM',
                    title='No Sales Activity',
                    message='No sales were recorded for the selected period.',
                    reference=reporting_period
                )
            )

        if sale_count > 0:
            average_sale = total_sales / sale_count

            high_value_sales = sales.filter(
                grand_total__gt=average_sale * Decimal('5')
            ).count()

            if high_value_sales > 0:
                alerts.append(
                    ComplianceIntelligenceService.create_alert(
                        organization=organization,
                        alert_type='SALES_PATTERN',
                        severity='MEDIUM',
                        title='Unusual High-Value Sales',
                        message='Some sales are significantly higher than the average sale value.',
                        reference=reporting_period
                    )
                )

        return alerts

    @staticmethod
    def analyze_payroll_anomalies(
        organization,
        reporting_period=None
    ):

        alerts = []

        # Payroll app may not exist yet.
        # This is a safe placeholder for future PAYE/payroll integration.

        return alerts

    @staticmethod
    def detect_fraud_risk(
        organization,
        reporting_period=None
    ):

        alerts = []

        duplicate_filings = (
            TaxFiling.objects.filter(
                organization=organization
            )
            .values('tax_type', 'reporting_period')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        for item in duplicate_filings:

            alerts.append(
                ComplianceIntelligenceService.create_alert(
                    organization=organization,
                    alert_type='FRAUD_RISK',
                    severity='CRITICAL',
                    title='Duplicate Tax Filing Detected',
                    message='More than one filing exists for the same tax type and reporting period.',
                    reference=f"{item['tax_type']}-{item['reporting_period']}"
                )
            )

        return alerts

    @staticmethod
    def generate_risk_score(
        organization,
        alerts
    ):

        score = Decimal('0.00')

        for alert in alerts:

            if alert.severity == 'LOW':
                score += Decimal('5')

            elif alert.severity == 'MEDIUM':
                score += Decimal('15')

            elif alert.severity == 'HIGH':
                score += Decimal('30')

            elif alert.severity == 'CRITICAL':
                score += Decimal('50')

        if score > 100:
            score = Decimal('100.00')

        risk_level = ComplianceIntelligenceService.get_risk_level(score)

        reason = f'{len(alerts)} compliance alert(s) generated.'

        profile = ComplianceRiskProfile.objects.create(
            organization=organization,
            risk_score=score,
            risk_level=risk_level,
            reason=reason
        )

        return profile

    @staticmethod
    def run_full_compliance_analysis(
        organization,
        reporting_period=None
    ):

        alerts = []

        alerts += ComplianceIntelligenceService.analyze_vat_anomalies(
            organization=organization,
            reporting_period=reporting_period
        )

        alerts += ComplianceIntelligenceService.analyze_refund_risk(
            organization=organization,
            reporting_period=reporting_period
        )

        alerts += ComplianceIntelligenceService.analyze_sales_patterns(
            organization=organization,
            reporting_period=reporting_period
        )

        alerts += ComplianceIntelligenceService.analyze_payroll_anomalies(
            organization=organization,
            reporting_period=reporting_period
        )

        alerts += ComplianceIntelligenceService.detect_fraud_risk(
            organization=organization,
            reporting_period=reporting_period
        )

        risk_profile = ComplianceIntelligenceService.generate_risk_score(
            organization=organization,
            alerts=alerts
        )

        run = ComplianceAnalysisRun.objects.create(
            organization=organization,
            analysis_type='FULL',
            reporting_period=reporting_period,
            total_alerts=len(alerts),
            highest_risk_level=risk_profile.risk_level
        )

        return {
            'analysis_run_id': run.id,
            'risk_score': risk_profile.risk_score,
            'risk_level': risk_profile.risk_level,
            'total_alerts': len(alerts),
            'alerts': alerts
        }