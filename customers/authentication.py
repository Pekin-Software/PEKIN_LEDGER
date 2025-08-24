from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from customers.models import Domain  # Adjust to your Domain model path
import logging

logger = logging.getLogger(__name__)

# class TenantAwareJWTAuthentication(JWTAuthentication):
#     def authenticate(self, request):
#         # First authenticate with JWT token
#         if request.path.endswith("/logout/"):
#             return super().authenticate(request)
        
#         raw_auth = super().authenticate(request)

#         if raw_auth is None:
#             return None  # No credentials provided

#         user, validated_token = raw_auth

#         # Tenant info from token (probably tenant ID or slug)
#         token_tenant = validated_token.get("tenant")
#         if not token_tenant:
#             raise AuthenticationFailed("Token missing tenant info.")

#         # Extract domain from request
#         host = request.get_host().split(':')[0]  # Remove port if any
#         # Try to find Domain object matching this host
#         try:
#             domain_obj = Domain.objects.get(domain=host)
#         except Domain.DoesNotExist:
#             logger.error(f"Domain object not found for host: {host}")
#             raise PermissionDenied("Request domain not recognized.")

#         request_tenant_id = str(domain_obj.tenant.id)

#         # Compare tenant from token with tenant of the request domain
#         if str(token_tenant) != request_tenant_id:
#             logger.warning(f"Tenant mismatch! Token tenant: {token_tenant}, Request tenant: {request_tenant_id}")
#             raise PermissionDenied("Tenant mismatch between token and request domain.")

#         # All good
#         return (user, validated_token)

class TenantAwareJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # For logout, fallback to default
        if request.path.endswith("/logout/"):
            return super().authenticate(request)

        # First try header
        raw_auth = super().authenticate(request)

        if raw_auth is None:
            # Try reading from cookie
            raw_token = request.COOKIES.get("access_token")
            if not raw_token:
                return None  # No token anywhere
            try:
                validated_token = self.get_validated_token(raw_token)
                user = self.get_user(validated_token)
                raw_auth = (user, validated_token)
            except Exception as e:
                logger.warning(f"Cookie JWT validation failed: {e}")
                return None

        user, validated_token = raw_auth

        # Tenant check
        token_tenant = validated_token.get("tenant")
        if not token_tenant:
            raise AuthenticationFailed("Token missing tenant info.")

        host = request.get_host().split(":")[0]
        try:
            domain_obj = Domain.objects.get(domain=host)
        except Domain.DoesNotExist:
            logger.error(f"Domain object not found for host: {host}")
            raise PermissionDenied("Request domain not recognized.")

        request_tenant_id = str(domain_obj.tenant.id)
        if str(token_tenant) != request_tenant_id:
            logger.warning(f"Tenant mismatch! Token tenant: {token_tenant}, Request tenant: {request_tenant_id}")
            raise PermissionDenied("Tenant mismatch between token and request domain.")

        return (user, validated_token)

