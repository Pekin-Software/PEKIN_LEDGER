from decimal import Decimal
from django.db import transaction
from django.db.models import  Sum, F, DecimalField, ExpressionWrapper


def update_dashboard_monthly_stat(sale):
    from .models import DashboardMonthlyStat

    tenant = sale.tenant
    date = sale.sale_date
    year = date.year
    month = date.month

    revenue = Decimal("0.00")
    cogs = Decimal("0.00")

    for item in sale.saledetail_set.all():
        revenue += item.quantity_sold * item.price_at_sale
        cogs += item.quantity_sold * item.lot.purchase_price

    profit = revenue - cogs

    with transaction.atomic():
        obj, _ = DashboardMonthlyStat.objects.select_for_update().get_or_create(
            tenant=tenant,
            year=year,
            month=month,
            defaults={
                "revenue": Decimal("0.00"),
                "cogs": Decimal("0.00"),
                "profit": Decimal("0.00"),
            }
        )

        obj.revenue += revenue
        obj.cogs += cogs
        obj.profit += profit
        obj.save()

def _compute_sale_totals(sale):
    from .models import DashboardMonthlyStat
    totals = sale.sale_details.aggregate(
        revenue=Sum(ExpressionWrapper(F('quantity_sold') * F('price_at_sale'), output_field=DecimalField())),
        cogs=Sum(ExpressionWrapper(F('quantity_sold') * F('lot__purchase_price'), output_field=DecimalField()))
    )
    revenue = totals['revenue'] or Decimal("0.00")
    cogs = totals['cogs'] or Decimal("0.00")
    return revenue, cogs, revenue - cogs

@transaction.atomic
def apply_sale_stats(sale):
    from .models import DashboardMonthlyStat
    """
    Apply stats only once (database protected)
    """

    sale = type(sale).objects.select_for_update().get(pk=sale.pk)

    if sale.stats_applied:
        return  # already counted safely

    revenue, cogs, profit = _compute_sale_totals(sale)

    stat, _ = DashboardMonthlyStat.objects.select_for_update().get_or_create(
        tenant=sale.tenant,
        year=sale.sale_date.year,
        month=sale.sale_date.month,
        defaults={"revenue": 0, "cogs": 0, "profit": 0},
    )

    stat.revenue += revenue
    stat.cogs += cogs
    stat.profit += profit
    stat.save()

    sale.stats_applied = True
    sale.save(update_fields=["stats_applied"])

@transaction.atomic
def reverse_sale_stats(sale):
    """
    Reverse stats safely (refund / cancel)
    """
    from .models import DashboardMonthlyStat 
    sale = type(sale).objects.select_for_update().get(pk=sale.pk)

    if not sale.stats_applied:
        return  # nothing to reverse

    revenue, cogs, profit = _compute_sale_totals(sale)

    stat = DashboardMonthlyStat.objects.select_for_update().get(
        tenant=sale.tenant,
        year=sale.sale_date.year,
        month=sale.sale_date.month,
    )

    stat.revenue -= revenue
    stat.cogs -= cogs
    stat.profit -= profit
    stat.save()

    sale.stats_applied = False
    sale.save(update_fields=["stats_applied"])