from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework import viewsets, status, permissions
from .models import Domain, User, Client
from .serializers import UserSerializer
from django.contrib.auth import authenticate
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render
from django.http import JsonResponse
from django_tenants.utils import schema_context
from rest_framework.permissions import IsAuthenticated
import logging
import os
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

logger = logging.getLogger(__name__)
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


        
#         

#         # Generate JWT tokens
#         refresh = RefreshToken.for_user(user)
#         access_token = str(refresh.access_token)

#         # Fetch the tenant domain
#         try:
#             tenant_domain = Domain.objects.get(tenant=user.domain).domain
#         except Domain.DoesNotExist:
#             print(f"Domain for tenant {user.domain} not found")  # Debugging line
#             return Response({"error": "Tenant domain not found"}, status=status.HTTP_400_BAD_REQUEST)

#         response_data = {
#             "role": user.position,
#             "tenant_domain": tenant_domain,  # Tenant subdomain
#             "user": user.username
#         }

#         # Create the JsonResponse
#         response = JsonResponse(response_data)

#         # Set secure cookies for JWT tokens
#         response.set_cookie(
#             'access_token', access_token, 
#             httponly=True, 
#             secure=True,        # Only sent over HTTPS
#             samesite='Strict',  # Prevents CSRF by restricting cookies to same-site requests
#             path='/'            # Cookie is available throughout the domain
#         )

#         response.set_cookie(
#             'refresh_token', str(refresh), 
#             httponly=True, 
#             secure=True,        # Only sent over HTTPS
#             samesite='Strict',  # Prevents CSRF by restricting cookies to same-site requests
#             path='/'
#         )

#         # Return the response
#         return response
    


class LoginViewSet(viewsets.ViewSet):

    @method_decorator(csrf_exempt) 
    @action(detail=False, methods=["post"])
    def login(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Login attempt for user: {username}")

        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            logger.warning(f"Authentication failed for username: {username}")
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            logger.warning(f"Authentication Successful for username: {username}")

        logger.info(f"User {username} authenticated successfully")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Ensure user has a valid tenant domain
        tenant_domain = None
        try:
            tenant_domain = Domain.objects.get(tenant=user.domain).domain
        except Domain.DoesNotExist:
            logger.error(f"Domain not found for tenant: {user.domain}")
            return Response({"error": "Tenant domain not found"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Login successful for user: {username}, Tenant Domain: {tenant_domain}")

        # response_data = {
        #     "role": user.position,
        #     "tenant_domain": tenant_domain,
        #     "user": user.username,
        #     "access_token": access_token,
        #     "refresh_token": str(refresh)
        # }

        # return Response(response_data, status=status.HTTP_200_OK)
        
        response_data = {
            "role": user.position,
            "tenant_domain": tenant_domain,  # Tenant subdomain
            "user": user.username,
            "access_token": access_token, 
        }

        # Create the JsonResponse
        response = Response(response_data, status=status.HTTP_200_OK)

        # Set secure cookies for JWT tokens
        response.set_cookie(
            'access_token', access_token, 
            httponly=True, 
            secure=False,        # Only sent over HTTPS
            samesite='Lax',  # Prevents CSRF by restricting cookies to same-site requests
            path='/'            # Cookie is available throughout the domain
        )

        response.set_cookie(
            'refresh_token', str(refresh), 
            httponly=True, 
            secure=False,        # Only sent over HTTPS
            samesite='Lax',  # Prevents CSRF by restricting cookies to same-site requests
            path='/'
        )
    
        # Return the response
        return response
    
    
    