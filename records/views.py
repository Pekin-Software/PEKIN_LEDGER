from rest_framework.response import Response
from rest_framework import viewsets, status, permissions
from customers.models import Domain, User
from customers.serializers import UserSerializer, StaffSerializer
from rest_framework.decorators import action
from django_tenants.utils import schema_context
from django.db.models import Q
from stores.models import Employee
class SubaccountViewSet(viewsets.ModelViewSet):
    """
    Handles user listing and subaccount creation in the tenant schema.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Admins see all users in their tenant; others see only their profile."""
        user = self.request.user
        if user.position == "Admin":
            return User.objects.filter(domain=user.domain)  # Admin sees all subaccounts
        return User.objects.filter(id=user.id)  # Others only see themselves
 
    @action(detail=False, methods=['post'], url_path='add_users')
    def create_subaccount(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.can_create_subaccount():
            return Response({"error": "Only Admins can create subaccounts."}, status=status.HTTP_403_FORBIDDEN)

        if user.domain is None:
            return Response({"error": "User does not belong to any domain."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data["domain"] = user.domain.id

        try:
            with schema_context(user.domain.schema_name):
                serializer = UserSerializer(data=data, context={'request': request})
                serializer.is_valid(raise_exception=True)
                serializer.save()

            return Response({
                "message": "Subaccount created successfully",
                "user": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            return Response({
                "error": str(e),
                "trace": traceback.format_exc()
            }, status=500)

    @action(detail=False, methods=['get'], url_path='staff')  # working
    def list_subaccounts(self, request):
        """
        Allows Admins to view all subaccounts in their tenant,
        excluding other Admins.
        """
        user = request.user

        if not user.can_create_subaccount():
            return Response({"error": "Only Admins can view staff."}, status=status.HTTP_403_FORBIDDEN)

        # Filter non-admin users in the same domain
        users = User.objects.filter(domain=user.domain).exclude(position='Admin')

        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch', 'delete'], url_path='staff') #working
    def manage_subaccount(self, request, pk=None):
        """Allows Admins to update or delete subaccounts."""
        user = request.user

        if not user.can_create_subaccount():
            return Response({"error": "Only Admins can manage subaccounts."}, status=status.HTTP_403_FORBIDDEN)

        try:
            subaccount = User.objects.get(pk=pk, domain=user.domain)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'PATCH':
            serializer = UserSerializer(subaccount, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Subaccount updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)

        elif request.method == 'DELETE':
            subaccount.delete()
            return Response({"message": "Subaccount deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get', 'patch'], url_path='profile') #working
    def user_profile(self, request):
        """Allows subaccounts to view and update their own profile."""
        user = request.user

        if request.method == 'GET':
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == 'PATCH':
            serializer = UserSerializer(user, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"message": "Profile updated successfully", "user": serializer.data}, status=status.HTTP_200_OK)
        
    @action(detail=False, methods=['get'], url_path='staff-unassigned')
    def list_unassigned_subaccounts(self, request):
        """
        List users in the same domain who are not assigned to any store.
        Only accessible by Admins.
        """
        user = request.user

        if not user.can_create_subaccount():
            return Response({"error": "Only Admins can view staff."}, status=status.HTTP_403_FORBIDDEN)

        # Get user IDs already assigned to stores
        assigned_user_ids = Employee.objects.values_list('user_id', flat=True)

        # Exclude Admins and users already assigned to any store
        unassigned_users = User.objects.filter(
            domain=user.domain
        ).exclude(
            id__in=assigned_user_ids
        ).exclude(
            position='Admin'
        )

        serializer = StaffSerializer(unassigned_users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)