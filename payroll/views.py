from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Employee, PayrollRun, PAYETaxBracket
from .serializers import EmployeeSerializer, PayrollRunSerializer, PAYETaxBracketSerializer
from reconciliation.serializers import (
    PayrollPaymentReconciliationSerializer,
    PAYEPaymentReconciliationSerializer
)

from payroll.payment_completion_service import (
    complete_full_payroll_payment
)
from .services import (
    generate_payroll_items,
    submit_payroll,
    approve_payroll,
    reject_payroll,
    create_payroll_journal_entry,
)

from stores.models import StoreUserAssignment


def is_admin(user):
    return (
        user.is_superuser
        or getattr(user, "role", None) == "ADMIN"
        or getattr(user, "position", None) == "ADMIN"
    )


def is_manager(user):
    return (
        getattr(user, "role", None) == "MANAGER"
        or getattr(user, "position", None) == "MANAGER"
    )


def is_auditor(user):
    return (
        getattr(user, "role", None) == "AUDITOR"
        or getattr(user, "position", None) == "AUDITOR"
    )

class PAYETaxBracketViewSet(viewsets.ModelViewSet):

    serializer_class = PAYETaxBracketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PAYETaxBracket.objects.filter(
            tenant=self.request.user.tenant
        )

    def perform_create(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant
        )

    def perform_update(self, serializer):
        serializer.save(
            tenant=self.request.user.tenant
        )

class PayrollViewSet(viewsets.ViewSet):

    permission_classes = [IsAuthenticated]

    # GET /api/payroll/store-employees/?store_id=1
    @action(detail=False, methods=["get"], url_path="store-employees")
    def store_employees(self, request):

        store_id = request.query_params.get("store_id")

        if not store_id:
            return Response(
                {"error": "store_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        assigned_user_ids = StoreUserAssignment.objects.filter(
            store_id=store_id,
            is_active=True
        ).values_list("user_id", flat=True)

        employees = Employee.objects.filter(
            user__tenant=request.user.tenant,
            user_id__in=assigned_user_ids,
            employment_status="ACTIVE"
        ).select_related("user")

        serializer = EmployeeSerializer(employees, many=True)

        return Response(serializer.data)


    # GET /api/payroll/master-employees/
    @action(detail=False, methods=["get"], url_path="master-employees")
    def master_employees(self, request):

        if not is_admin(request.user):
            return Response(
                {"error": "Only admin can view master employees"},
                status=status.HTTP_403_FORBIDDEN
            )

        employees = Employee.objects.filter(
            user__tenant=request.user.tenant
        ).select_related("user")

        serializer = EmployeeSerializer(employees, many=True)

        return Response(serializer.data)


    # POST /api/payroll/create-payroll/
    @action(detail=False, methods=["post"], url_path="create-payroll")
    def create_payroll(self, request):

        if not is_manager(request.user):
            return Response(
                {"error": "Only store manager can create payroll"},
                status=status.HTTP_403_FORBIDDEN
            )

        store_id = request.data.get("store")
        payroll_month = request.data.get("payroll_month")
        payroll_year = request.data.get("payroll_year")

        if not store_id or not payroll_month or not payroll_year:
            return Response(
                {
                    "error": "store, payroll_month, and payroll_year are required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        is_assigned_manager = StoreUserAssignment.objects.filter(
            user=request.user,
            store_id=store_id,
            is_active=True
        ).exists()

        if not is_assigned_manager:
            return Response(
                {"error": "You are not assigned to this store"},
                status=status.HTTP_403_FORBIDDEN
            )

        payroll_run, created = PayrollRun.objects.get_or_create(
            tenant=request.user.tenant,
            store_id=store_id,
            payroll_month=payroll_month,
            payroll_year=payroll_year,
            defaults={
                "created_by": request.user,
                "status": "DRAFT"
            }
        )

        if not created:
            return Response(
                {"error": "Payroll already exists for this store and period"},
                status=status.HTTP_400_BAD_REQUEST
            )

        generate_payroll_items(payroll_run.id)
        payroll_run = submit_payroll(payroll_run.id)

        serializer = PayrollRunSerializer(payroll_run)

        return Response(
            {
                "message": "Payroll created, items generated, and submitted successfully",
                "payroll": serializer.data
            },
            status=status.HTTP_201_CREATED
        )


    # GET /api/payroll/payroll/
    # GET /api/payroll/payroll/?store_id=1
    @action(detail=False, methods=["get"], url_path="payroll")
    def payroll(self, request):

        store_id = request.query_params.get("store_id")

        if not (
            is_admin(request.user)
            or is_manager(request.user)
            or is_auditor(request.user)
        ):
            return Response(
                {"error": "You do not have permission to view payroll"},
                status=status.HTTP_403_FORBIDDEN
            )

        payroll_runs = PayrollRun.objects.filter(
            tenant=request.user.tenant
        ).select_related("tenant", "store")

        if store_id:
            payroll_runs = payroll_runs.filter(store_id=store_id)

            if is_manager(request.user):
                assigned = StoreUserAssignment.objects.filter(
                    user=request.user,
                    store_id=store_id,
                    is_active=True
                ).exists()

                if not assigned:
                    return Response(
                        {"error": "You are not assigned to this store"},
                        status=status.HTTP_403_FORBIDDEN
                    )

        elif is_manager(request.user):
            assigned_store_ids = StoreUserAssignment.objects.filter(
                user=request.user,
                is_active=True
            ).values_list("store_id", flat=True)

            payroll_runs = payroll_runs.filter(
                store_id__in=assigned_store_ids
            )

        serializer = PayrollRunSerializer(payroll_runs, many=True)

        return Response(serializer.data)


    # POST /api/payroll/{id}/approve/
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):

        if not is_admin(request.user):
            return Response(
                {"error": "Only admin can approve payroll"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            payroll_run = approve_payroll(
                payroll_run_id=pk,
                admin_user=request.user
            )

            entry = create_payroll_journal_entry(
                payroll_run_id=payroll_run.id,
                admin_user=request.user
            )

            payroll_run.refresh_from_db()

            serializer = PayrollRunSerializer(payroll_run)

            return Response(
                {
                    "message": "Payroll approved and posted to ledger successfully",
                    "journal_entry_id": entry.id,
                    "payroll": serializer.data
                },
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    # POST /api/payroll/{id}/reject/
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):

        if not is_admin(request.user):
            return Response(
                {"error": "Only admin can reject payroll"},
                status=status.HTTP_403_FORBIDDEN
            )

        payroll_run = reject_payroll(
            payroll_run_id=pk,
            admin_user=request.user
        )

        serializer = PayrollRunSerializer(payroll_run)

        return Response(serializer.data)


    # POST /api/payroll/{id}/post-to-ledger/
    @action(detail=True, methods=["post"], url_path="post-to-ledger")
    def post_to_ledger(self, request, pk=None):

        if not is_admin(request.user):
            return Response(
                {"error": "Only admin can post payroll to ledger"},
                status=status.HTTP_403_FORBIDDEN
            )

        entry = create_payroll_journal_entry(
            payroll_run_id=pk,
            admin_user=request.user
        )

        return Response(
            {
                "message": "Payroll posted to ledger successfully",
                "journal_entry_id": entry.id
            },
            status=status.HTTP_200_OK
        )
    
    @action(
        detail=False,
        methods=['post'],
        url_path='pay-payroll'
    )
    def pay_payroll(self, request):

        if not is_admin(request.user):
            return Response(
                {
                    'error': 'Only admin can complete payroll payment.'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        payroll_run_id = request.data.get(
            'payroll_run_id'
        )

        payroll_run = PayrollRun.objects.get(
            id=payroll_run_id,
            tenant=request.user.tenant
        )

        result = complete_full_payroll_payment(
            payroll_run=payroll_run,

            salary_payment_method=request.data.get(
                'salary_payment_method'
            ),

            salary_transaction_reference=request.data.get(
                'salary_transaction_reference'
            ),

            salary_provider=request.data.get(
                'salary_provider'
            ),

            paye_payment_method=request.data.get(
                'paye_payment_method'
            ),

            paye_transaction_reference=request.data.get(
                'paye_transaction_reference'
            ),

            paye_provider=request.data.get(
                'paye_provider'
            ),

            paid_by=request.user
        )

        return Response(
            {
                'message':
                'Salary and PAYE payments completed and reconciled automatically',

                'salary_reconciliation':
                PayrollPaymentReconciliationSerializer(
                    result['salary_reconciliation']
                ).data,

                'paye_reconciliation':
                PAYEPaymentReconciliationSerializer(
                    result['paye_reconciliation']
                ).data,
            },

            status=status.HTTP_201_CREATED
        )