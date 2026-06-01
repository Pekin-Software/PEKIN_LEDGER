from decimal import Decimal

from django.db.models import Sum, Count

from sales.models import Sale
from taxation.models import VATLedger
from compliance.models import TaxFiling

from .models import (
    ComplianceAlert,
    ComplianceRiskProfile,
    ComplianceAnalysisRun
)


class AIAnalyticsService:

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
        business_name,
        alert_type,
        severity,
        title,
        message,
        reference=None
    ):
        return ComplianceAlert.objects.create(
            business_name=business_name,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            reference=reference
        )

    @staticmethod
    def analyze_vat_anomalies(
        business_name,
        reporting_period
    ):
        alerts = []

        vat_entries = VATLedger.objects.filter(
            organization=business_name,
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
                AIAnalyticsService.create_alert(
                    business_name=business_name,
                    alert_type='VAT_ANOMALY',
                    severity='HIGH',
                    title='No Output VAT Recorded',
                    message='No output VAT was recorded for this reporting period.',
                    reference=reporting_period
                )
            )

        if input_vat > output_vat:
            alerts.append(
                AIAnalyticsService.create_alert(
                    business_name=business_name,
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
                    AIAnalyticsService.create_alert(
                        business_name=business_name,
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
        business_name,
        reporting_period
    ):
        alerts = []

        filing = TaxFiling.objects.filter(
            organization=business_name,
            tax_type='VAT',
            reporting_period=reporting_period
        ).first()

        if not filing:
            return alerts

        if filing.net_tax_payable < 0:
            alerts.append(
                AIAnalyticsService.create_alert(
                    business_name=business_name,
                    alert_type='REFUND_RISK',
                    severity='HIGH',
                    title='VAT Refund Position Detected',
                    message='This VAT filing shows a refund position. Review input VAT documents.',
                    reference=reporting_period
                )
            )

        return alerts

    @staticmethod
    def analyze_sales_patterns(
        business_name,
        reporting_period=None
    ):
        alerts = []

        sales = Sale.objects.filter(
            organization=business_name
        )

        if reporting_period:
            year, month = reporting_period.split('-')

            sales = sales.filter(
                created_at__year=int(year),
                created_at__month=int(month)
            )

        sale_count = sales.count()

        total_sales = sales.aggregate(
            total=Sum('grand_total')
        )['total'] or Decimal('0.00')

        if sale_count == 0:
            alerts.append(
                AIAnalyticsService.create_alert(
                    business_name=business_name,
                    alert_type='SALES_PATTERN',
                    severity='MEDIUM',
                    title='No Sales Activity',
                    message='No sales were recorded for this period.',
                    reference=reporting_period
                )
            )
            return alerts

        average_sale = total_sales / sale_count

        high_value_sales = sales.filter(
            grand_total__gt=average_sale * Decimal('5')
        ).count()

        if high_value_sales > 0:
            alerts.append(
                AIAnalyticsService.create_alert(
                    business_name=business_name,
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
        business_name,
        reporting_period=None
    ):

        from payroll.models import PayrollRun

        alerts = []

        payroll_runs = PayrollRun.objects.filter(
            organization=business_name
        )

        if reporting_period:

            year, month = reporting_period.split('-')

            payroll_runs = payroll_runs.filter(
                payroll_date__year=int(year),
                payroll_date__month=int(month)
            )

        total_payroll = payroll_runs.aggregate(
            total=Sum('net_salary')
        )['total'] or Decimal('0.00')

        total_tax = payroll_runs.aggregate(
            total=Sum('paye_amount')
        )['total'] or Decimal('0.00')

        employee_count = payroll_runs.count()

        # -----------------------------------
        # NO PAYROLL
        # -----------------------------------

        if employee_count == 0:

            alerts.append(
                AIAnalyticsService.create_alert(
                    business_name=business_name,
                    alert_type='PAYROLL_ANOMALY',
                    severity='MEDIUM',
                    title='No Payroll Records',
                    message='No payroll records found for this reporting period.',
                    reference=reporting_period
                )
            )

            return alerts

        # -----------------------------------
        # HIGH PAYROLL TAX RATIO
        # -----------------------------------

        if total_payroll > 0:

            payroll_tax_ratio = (
                total_tax / total_payroll
            ) * Decimal('100')

            if payroll_tax_ratio > Decimal('40'):

                alerts.append(
                    AIAnalyticsService.create_alert(
                        business_name=business_name,
                        alert_type='PAYROLL_ANOMALY',
                        severity='HIGH',
                        title='High Payroll Tax Ratio',
                        message='Payroll taxes are unusually high compared to total payroll.',
                        reference=reporting_period
                    )
                )

        # -----------------------------------
        # ABNORMAL PAYROLL SPIKES
        # -----------------------------------

        average_salary = (
            total_payroll / employee_count
        )

        abnormal_payrolls = payroll_runs.filter(
            net_salary__gt=(
                average_salary
                * Decimal('5')
            )
        ).count()

        if abnormal_payrolls > 0:

            alerts.append(
                AIAnalyticsService.create_alert(
                    business_name=business_name,
                    alert_type='PAYROLL_ANOMALY',
                    severity='HIGH',
                    title='Abnormal Payroll Spike',
                    message='Some payroll entries are significantly higher than average salaries.',
                    reference=reporting_period
                )
            )

        # -----------------------------------
        # ZERO TAX DEDUCTIONS
        # -----------------------------------

        zero_tax_count = payroll_runs.filter(
            paye_amount=0
        ).count()

        if zero_tax_count > 0:

            alerts.append(
                AIAnalyticsService.create_alert(
                    business_name=business_name,
                    alert_type='PAYROLL_ANOMALY',
                    severity='MEDIUM',
                    title='Employees Without PAYE',
                    message='Some payroll records have zero PAYE deductions.',
                    reference=reporting_period
                )
            )

        return alerts

        @staticmethod
        def detect_fraud_risk(
            business_name,
            reporting_period=None
        ):
            alerts = []

            duplicate_filings = (
                TaxFiling.objects.filter(
                    organization=business_name
                )
                .values(
                    'tax_type',
                    'reporting_period'
                )
                .annotate(
                    count=Count('id')
                )
                .filter(
                    count__gt=1
                )
            )

            for item in duplicate_filings:
                alerts.append(
                    AIAnalyticsService.create_alert(
                        business_name=business_name,
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
        business_name,
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

        risk_level = AIAnalyticsService.get_risk_level(
            score
        )

        return ComplianceRiskProfile.objects.create(
            business_name=business_name,
            risk_score=score,
            risk_level=risk_level,
            reason=f'{len(alerts)} compliance alert(s) generated.'
        )

    @staticmethod
    def run_full_analysis(
        business_name,
        reporting_period=None
    ):
        alerts = []

        alerts += AIAnalyticsService.analyze_vat_anomalies(
            business_name=business_name,
            reporting_period=reporting_period
        )

        alerts += AIAnalyticsService.analyze_refund_risk(
            business_name=business_name,
            reporting_period=reporting_period
        )

        alerts += AIAnalyticsService.analyze_sales_patterns(
            business_name=business_name,
            reporting_period=reporting_period
        )

        alerts += AIAnalyticsService.analyze_payroll_anomalies(
            business_name=business_name,
            reporting_period=reporting_period
        )

        alerts += AIAnalyticsService.detect_fraud_risk(
            business_name=business_name,
            reporting_period=reporting_period
        )

        risk_profile = AIAnalyticsService.generate_risk_score(
            business_name=business_name,
            alerts=alerts
        )

        run = ComplianceAnalysisRun.objects.create(
            business_name=business_name,
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