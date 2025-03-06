from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import viewsets, status, permissions
from .models import Domain, User, Client
from .serializers import UserSerializer
from django.contrib.auth import authenticate
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render
from django_tenants.utils import schema_context
from rest_framework.permissions import IsAuthenticated

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.position == 'Admin'

class UserViewSet(viewsets.ModelViewSet):
    """
    Handles:
    - Main user (Tenant Owner) registration
    - Subaccount creation (by Admins within their tenant)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Allow main registration

    def create(self, request, *args, **kwargs):
        """
        - If no user is logged in → Creates a Main Account (Tenant + Admin).
        - If an Admin is logged in → Creates a Subaccount inside the tenant schema.
        """
        if request.user.is_authenticated:  
            if request.user.position != "Admin":
                return Response({"error": "Only Admins can create subaccounts."}, status=status.HTTP_403_FORBIDDEN)

            # Subaccounts must be created inside the Admin's tenant
            with schema_context(request.user.domain.schema_name):
                request.data["domain"] = request.user.domain.id  # Link to tenant
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

            return Response({
                'message': 'Subaccount created successfully inside tenant',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)

        # If no user is logged in → Register a new Main Account
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({
            'message': 'Main account (Tenant) created successfully',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        """Admins see all users in their tenant, others only see themselves."""
        user = self.request.user
        if user.is_authenticated and user.position == "Admin":
            return User.objects.filter(domain=user.domain)  # Admin sees all in schema
        return User.objects.filter(id=user.id)  # Others only see themselves
    def perform_create(self, serializer):
        """Ensure users are created within the correct tenant schema."""
        serializer.save(domain=self.request.user.domain)


def index(request):
    return(HttpResponse("<h1>Public</h1>"))

class LoginViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def login(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        print(f"Trying to authenticate user: {username}")  # Debugging line
        # Authenticate the user
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            print(f"Authentication failed for {username}")  # Debugging line
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Fetch the tenant domain
        try:
            tenant_domain = Domain.objects.get(tenant=user.domain).domain
        except Domain.DoesNotExist:
            print(f"Domain for tenant {user.domain} not found")  # Debugging line
            return Response({"error": "Tenant domain not found"}, status=status.HTTP_400_BAD_REQUEST)

        # return Response({
        #     "access_token": access_token,
        #     "refresh_token": str(refresh),
        #     "redirect_url": f"http://{tenant_domain}:8000/",
        # }, status=status.HTTP_200_OK)
        return render(request, 'redirect_page.html', {
            'redirect_url': f'http://{tenant_domain}:8000/api/users/staff/',  # Pass the URL to the template
            'access_token': access_token,
            'refresh_token': str(refresh)
        })