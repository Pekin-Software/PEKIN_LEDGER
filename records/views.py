from rest_framework.response import Response
from rest_framework import viewsets, status, permissions
from customers.models import Domain, User
from customers.serializers import UserSerializer
from rest_framework.decorators import action
from django_tenants.utils import schema_context


# class SubaccountViewSet(viewsets.ModelViewSet):
#     """
#     Allows only Admins to create and list subaccounts within their tenant.
#     """
#     serializer_class = UserSerializer
#     permission_classes = [permissions.IsAuthenticated]  # User must be logged in

#     def get_queryset(self):
#         """Admins see all users in their tenant, others only see themselves."""
#         user = self.request.user
#         if user.position == "Admin":
#             return User.objects.filter(domain=user.domain)  # Admin sees all in schema
#         return User.objects.filter(id=user.id)  # Others only see themselves

#     def create(self, request, *args, **kwargs):
#         """Allows Admins to create subaccounts inside their tenant schema."""
#         user = request.user

#         # Only Admins can create subaccounts
#         if not user.can_create_subaccount():
#             return Response({"error": "Only Admins can create subaccounts."}, status=status.HTTP_403_FORBIDDEN)

#         # Ensure the subaccount is created within the correct tenant schema
#         with schema_context(user.domain.schema_name):
#             request.data["domain"] = user.domain.id  # Link subaccount to Admin's tenant
#             serializer = self.get_serializer(data=request.data)
#             serializer.is_valid(raise_exception=True)
#             serializer.save()

#         return Response({
#             'message': 'Subaccount created successfully within tenant',
#             'user': serializer.data
#         }, status=status.HTTP_201_CREATED)

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

    
    # @action(detail=False, methods=['post'], url_path='add_users')
    # def create_subaccount(self, request):
    #     """Allows Admins to create subaccounts within their tenant."""
    #     user = request.user

    #     # Only Admins can create subaccounts
    #     if not user.can_create_subaccount():
    #         return Response({"error": "Only Admins can create subaccounts."}, status=status.HTTP_403_FORBIDDEN)

    #     # Pass the request context to the serializer to ensure the subaccount gets the correct domain
    #     with schema_context(user.domain.schema_name):
    #         request.data["domain"] = user.domain.id  # Ensure subaccount is linked to the tenant

    #         # Now pass 'request' context to serializer so it can reference the domain and admin user
    #         serializer = UserSerializer(data=request.data, context={'request': request})

    #         # Validate and save the subaccount
    #         serializer.is_valid(raise_exception=True)
    #         serializer.save()

    #     return Response({"message": "Subaccount created successfully", "user": serializer.data}, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='add_users')
    # def create_subaccount(self, request):
    #     """Allows Admins to create subaccounts within their tenant."""
    #     user = request.user

    #     # Only Admins can create subaccounts
    #     if not user.can_create_subaccount():
    #         return Response({"error": "Only Admins can create subaccounts."}, status=status.HTTP_403_FORBIDDEN)

    #     # Ensure the user has a domain
    #     if user.domain is None:
    #         return Response({"error": "User does not belong to any domain."}, status=status.HTTP_400_BAD_REQUEST)

    #     # Pass the request context to the serializer to ensure the subaccount gets the correct domain
    #     with schema_context(user.domain.schema_name):
    #         request.data["domain"] = user.domain.id  # Ensure subaccount is linked to the tenant

    #         # Now pass 'request' context to serializer so it can reference the domain and admin user
    #         serializer = UserSerializer(data=request.data, context={'request': request})

    #         # Validate and save the subaccount
    #         serializer.is_valid(raise_exception=True)
    #         serializer.save()

    #     return Response({"message": "Subaccount created successfully", "user": serializer.data}, status=status.HTTP_201_CREATED)
    def create_subaccount(self, request):
        """Allows Admins to create subaccounts within their tenant."""
        user = request.user

        # Only Admins can create subaccounts
        if not user.can_create_subaccount():
            return Response({"error": "Only Admins can create subaccounts."}, status=status.HTTP_403_FORBIDDEN)

        # Ensure the user has a domain (Admin must have a domain)
        if user.domain is None:
            return Response({"error": "User does not belong to any domain."}, status=status.HTTP_400_BAD_REQUEST)
        
        request.data["domain"] = user.domain.id  # Ensure subaccount is linked to the Admin's tenant
        
        # Pass the request context to the serializer to ensure the subaccount gets the correct domain
        with schema_context(user.domain.schema_name):
           

            # Now pass 'request' context to serializer so it can reference the domain and admin user
            serializer = UserSerializer(data=request.data, context={'request': request})

            # Validate and save the subaccount
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response({"message": "Subaccount created successfully", "user": serializer.data}, status=status.HTTP_201_CREATED)


    @action(detail=False, methods=['get'], url_path='staff')
    def list_subaccounts(self, request):
        """Allows Admins to view all subaccounts in their tenant."""
        user = request.user

        if not user.can_create_subaccount():
            return Response({"error": "Only Admins can view staff."}, status=status.HTTP_403_FORBIDDEN)

        users = User.objects.filter(domain=user.domain)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch', 'delete'], url_path='staff')
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

    @action(detail=False, methods=['get', 'patch'], url_path='profile')
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