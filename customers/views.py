from rest_framework.response import Response
from rest_framework import viewsets, status, permissions
from .models import Domain, User
from stores.models import Employee
from finance.models import ExchangeRate
from .serializers import UserSerializer
from django.contrib.auth import authenticate
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django_tenants.utils import schema_context
from rest_framework.permissions import IsAuthenticated, AllowAny
import logging
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import traceback
from rest_framework_simplejwt.views import TokenRefreshView

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


class CookieTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]  # public; relies on cookie

    def post(self, request, *args, **kwargs):
        # Try body first, fallback to cookie
        refresh_token = request.data.get("refresh") or request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response({"error": "Refresh token missing."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_401_UNAUTHORIZED)

        data = serializer.validated_data  # contains 'access' and maybe 'refresh' if rotation is enabled

        response = Response(data, status=status.HTTP_200_OK)

        # If rotating refresh tokens, set the new one in cookie
        if "refresh" in data:
            response.set_cookie(
                key="refresh_token",
                value=data["refresh"],
                domain=getattr(settings, "TENANT_COOKIE_DOMAIN", None),  # .pekingledger.store
                path="/",
                httponly=True,
                secure=getattr(settings, "SECURE_COOKIE", True),
                samesite="None",
                max_age=int(serializer.token.lifetime.total_seconds()) if hasattr(serializer, "token") else None,
            )

        return response
    

# class LoginViewSet(viewsets.ViewSet):
#     # Dynamic cookie settings based on DEBUG
#     # cookie_settings = {
#     #         'path': '/',
#     #         'domain': '.pekingledger.store',
#     #         'samesite': 'None',
#     #         'secure': True,
#     #     }


#     @method_decorator(csrf_exempt)
#     @action(detail=False, methods=["post"])
#     # def login(self, request):
#     #     try:
#     #         username = request.data.get("username")
#     #         password = request.data.get("password")

#     #         if not username or not password:
#     #             return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

#     #         logger.info(f"Login attempt for user: {username}")

#     #         user = authenticate(request, username=username, password=password)
#     #         if user is None:
#     #             logger.warning(f"Authentication failed for username: {username}")
#     #             return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

#     #         logger.info(f"Authentication successful for user: {username}")

#     #         refresh = RefreshToken.for_user(user)
#     #         refresh["tenant"] = str(user.domain.id)
#     #         access_token = str(refresh.access_token)

#     #         try:
#     #             tenant_domain = Domain.objects.get(tenant=user.domain).domain
                
#     #         except Domain.DoesNotExist:
#     #             logger.error(f"Domain not found for tenant: {user.domain}")
#     #             return Response({"error": "Tenant domain not found"}, status=status.HTTP_400_BAD_REQUEST)

#     #         try:
#     #             with schema_context(user.domain.schema_name):
#     #                 # Default values
#     #                 store_id = None
#     #                 latest_usd_rate = None

#     #                 # Store lookup
#     #                 try:
#     #                     store_employee = Employee.objects.get(user=user)
#     #                     store_id = store_employee.store.id
#     #                 except Employee.DoesNotExist:
#     #                     logger.warning(f"No store association found for user {user.username}")

#     #                 # Exchange rate lookup
#     #                 exchange_rate = ExchangeRate.objects.filter(tenant=user.domain).order_by('-effective_date').first()
#     #                 if exchange_rate:
#     #                     latest_usd_rate = exchange_rate.usd_rate
#     #         except Exception as e:
#     #             logger.error(f"Error fetching tenant-specific data: {str(e)}")
#     #             store_id = None
#     #             latest_usd_rate = None
                
#     #         response_data = {
#     #             "id": user.id,
#     #             "role": user.position,
#     #             "tenant_domain": tenant_domain,
#     #             "user": user.username,
#     #             "access_token": access_token,
#     #             "business_name": user.domain.business_name,
#     #             "store_id": store_id, 
#     #             "exchange_rate": latest_usd_rate
#     #         }

#     #         response = Response(response_data, status=status.HTTP_200_OK)
#     #         return response

#     #     except Exception as e:
#     #         logger.error(f"Login failed: {str(e)}")
#     #         return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     @method_decorator(csrf_exempt)
#     @action(detail=False, methods=["post"])
#     def login(self, request):
#         try:
#             username = request.data.get("username")
#             password = request.data.get("password")

#             if not username or not password:
#                 return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

#             logger.info(f"Login attempt for user: {username}")
#             user = authenticate(request, username=username, password=password)
#             if user is None:
#                 logger.warning(f"Authentication failed for username: {username}")
#                 return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

#             logger.info(f"Authentication successful for user: {username}")

#             # Create tokens
#             refresh = RefreshToken.for_user(user)
#             refresh["tenant"] = str(user.domain.id)
#             access_token = str(refresh.access_token)
#             refresh_token = str(refresh)

#             try:
#                 tenant_domain = Domain.objects.get(tenant=user.domain).domain
#             except Domain.DoesNotExist:
#                 logger.error(f"Domain not found for tenant: {user.domain}")
#                 return Response({"error": "Tenant domain not found"}, status=status.HTTP_400_BAD_REQUEST)

#             # Tenant-specific optional data
#             try:
#                 with schema_context(user.domain.schema_name):
#                     store_id = None
#                     latest_usd_rate = None
#                     try:
#                         store_employee = Employee.objects.get(user=user)
#                         store_id = store_employee.store.id
#                     except Employee.DoesNotExist:
#                         logger.warning(f"No store association found for user {user.username}")

#                     exchange_rate = ExchangeRate.objects.filter(tenant=user.domain).order_by('-effective_date').first()
#                     if exchange_rate:
#                         latest_usd_rate = exchange_rate.usd_rate
#             except Exception as e:
#                 logger.error(f"Error fetching tenant-specific data: {str(e)}")
#                 store_id = None
#                 latest_usd_rate = None

#             response_data = {
#                 "id": user.id,
#                 "role": user.position,
#                 "tenant_domain": tenant_domain,
#                 "user": user.username,
#                 "business_name": user.domain.business_name,
#                 "store_id": store_id,
#                 "exchange_rate": latest_usd_rate,
#                 "access_token": access_token,          # keep returning access token
#                 # "refresh_token": refresh_token       # ⛔️ do NOT return this anymore
#             }

#             resp = Response(response_data, status=status.HTTP_200_OK)

#             # 🍪 Set refresh token as HttpOnly cookie for all subdomains
#             cookie_kwargs = {
#                 "key": "refresh_token",
#                 "value": refresh_token,
#                 "domain": getattr(settings, "TENANT_COOKIE_DOMAIN", None),  # ".pekingledger.store"
#                 "path": "/",
#                 "httponly": True,
#                 "secure": getattr(settings, "SECURE_COOKIE", True),
#                 "samesite": "None",   # cross-site across subdomains
#                 "max_age": int(RefreshToken.lifetime.total_seconds()) if hasattr(RefreshToken, "lifetime") else None,
#             }
#             resp.set_cookie(**cookie_kwargs)

#             return resp

#         except Exception as e:
#             logger.error(f"Login failed: {str(e)}")
#             return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)            
#     # @method_decorator(csrf_exempt)
#     # @action(detail=False, methods=["post"])
#     # def logout(self, request):
#     #     response = Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
#     #     return response

#     @method_decorator(csrf_exempt)
#     @action(detail=False, methods=["post"])
#     def logout(self, request):
#         try:
#             # 1) Prefer cookie
#             refresh_token = request.COOKIES.get("refresh_token")

#             # 2) Fallback to body if provided
#             if not refresh_token:
#                 refresh_token = request.data.get("refresh_token")

#             if not refresh_token:
#                 return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

#             try:
#                 token = RefreshToken(refresh_token)
#                 token.blacklist()
#             except Exception as e:
#                 logger.warning(f"Invalid refresh token during logout: {str(e)}")
#                 # Even if invalid, clear cookie to be safe
#                 resp = Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)
#                 resp.delete_cookie(
#                     key="refresh_token",
#                     domain=getattr(settings, "TENANT_COOKIE_DOMAIN", None),
#                     path="/",
#                 )
#                 return resp

#             logger.info("Logout successful — refresh token blacklisted.")
#             resp = Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
#             resp.delete_cookie(
#                 key="refresh_token",
#                 domain=getattr(settings, "TENANT_COOKIE_DOMAIN", None),
#                 path="/",
#             )
#             return resp

#         except Exception as e:
#             logger.error(f"Logout failed: {str(e)}")
#             return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginViewSet(viewsets.ViewSet):
    @method_decorator(csrf_exempt)
    @action(detail=False, methods=["post"])
    def login(self, request):
        try:
            username = request.data.get("username")
            password = request.data.get("password")

            if not username or not password:
                return Response({"error": "Username and password are required."}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"Login attempt for user: {username}")
            user = authenticate(request, username=username, password=password)
            if user is None:
                logger.warning(f"Authentication failed for username: {username}")
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

            logger.info(f"Authentication successful for user: {username}")

            # Create tokens
            refresh = RefreshToken.for_user(user)
            refresh["tenant"] = str(user.domain.id)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            try:
                tenant_domain = Domain.objects.get(tenant=user.domain).domain
            except Domain.DoesNotExist:
                logger.error(f"Domain not found for tenant: {user.domain}")
                return Response({"error": "Tenant domain not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Tenant-specific optional data
            try:
                with schema_context(user.domain.schema_name):
                    store_id = None
                    latest_usd_rate = None
                    try:
                        store_employee = Employee.objects.get(user=user)
                        store_id = store_employee.store.id
                    except Employee.DoesNotExist:
                        logger.warning(f"No store association found for user {user.username}")

                    exchange_rate = ExchangeRate.objects.filter(tenant=user.domain).order_by('-effective_date').first()
                    if exchange_rate:
                        latest_usd_rate = exchange_rate.usd_rate
            except Exception as e:
                logger.error(f"Error fetching tenant-specific data: {str(e)}")
                store_id = None
                latest_usd_rate = None

            response_data = {
                "id": user.id,
                "role": user.position,
                "tenant_domain": tenant_domain,
                "user": user.username,
                "business_name": user.domain.business_name,
                "store_id": store_id,
                "exchange_rate": latest_usd_rate,
                "access_token": access_token,  # return access token for SPA/API
            }

            resp = Response(response_data, status=status.HTTP_200_OK)

            # 🍪 Set refresh token as HttpOnly cookie for all subdomains
            is_prod = not settings.DEBUG
            cookie_domain = ".pekingledger.store" if is_prod else None  # local dev leaves domain None

            # Set refresh token cookie
            resp.set_cookie(
                key="refresh_token",
                value=refresh_token,
                domain=cookie_domain,
                path="/",
                httponly=True,
                secure=is_prod,  # secure in production
                samesite="None",  # cross-subdomain usage
                max_age=int(RefreshToken.lifetime.total_seconds()) if hasattr(RefreshToken, "lifetime") else None,
            )

            # Set access token cookie as well
            resp.set_cookie(
                key="access_token",
                value=access_token,
                domain=cookie_domain,
                path="/",
                httponly=True,
                secure=is_prod,
                samesite="None",  # allows cross-subdomain usage
                max_age=int(refresh.access_token.lifetime.total_seconds()) if hasattr(refresh.access_token, "lifetime") else None,
            )

            return resp

        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=["post"])
    def logout(self, request):
        try:
            refresh_token = request.COOKIES.get("refresh_token") or request.data.get("refresh_token")
            if not refresh_token:
                return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception as e:
                logger.warning(f"Invalid refresh token during logout: {str(e)}")

            resp = Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
            cookie_domain = ".pekingledger.store" if not settings.DEBUG else None
            resp.delete_cookie(key="refresh_token", domain=cookie_domain, path="/")

            return resp

        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





