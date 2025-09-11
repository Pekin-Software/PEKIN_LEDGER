from pathlib import Path
import dj_database_url
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------------------
# SECURITY (HARDCODED FOR FIRST DEPLOY)
# ------------------------------------------------------------------------------
SECRET_KEY = "django-insecure-_!gb#a3e10(y9ur98k1h(pc2(w&+2*+v+jj*86s#lj2#)$xb86"
DEBUG = False
ALLOWED_HOSTS = [".elasticbeanstalk.com",
                "api.pekinledger.com", ".api.pekinledger.com",  
                "localhost",
                "127.0.0.1",
                ]

# ------------------------------------------------------------------------------
# APPLICATIONS
# ------------------------------------------------------------------------------
SHARED_APPS = [
    "django_tenants",
    "customers",
    "django_extensions",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "storages",
]

TENANT_APPS = [
    "client_app",
    "inventory",
    "products",
    "records",
    "stores",
    "sales",
    "order",
    "finance",
]

INSTALLED_APPS = SHARED_APPS + [app for app in TENANT_APPS if app not in SHARED_APPS]

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "ledger_api.urls"
WSGI_APPLICATION = "ledger_api.wsgi.application"

# ------------------------------------------------------------------------------
# DATABASE (HARDCODED)
# ------------------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=(
            "postgres://ledgerdbadmin:[L5RfBblzzY):YZDsD$-4vAVw6:ck#"
            "@ledger-aurora-cluster.cluster-cgzs8geqks83.us-east-1.rds.amazonaws.com:5432/ledgerdb"
        ),
        engine="django_tenants.postgresql_backend",
    )
}

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

# ------------------------------------------------------------------------------
# REST FRAMEWORK & JWT
# ------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "customers.authentication.TenantAwareJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "EXCEPTION_HANDLER": "customers.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
}

# ------------------------------------------------------------------------------
# CORS (HARDCODED)
# ------------------------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://app.pekingledger.com",
    "https://api.pekinledger.com",
]
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https:\/\/.*\.api\.pekinledger\.com$"]
CORS_ALLOW_HEADERS = ["content-type", "authorization"]

# ------------------------------------------------------------------------------
# STATIC & MEDIA (S3 + CLOUDFRONT)
# ------------------------------------------------------------------------------
AWS_STORAGE_BUCKET_NAME = "ledger-static-media"
AWS_S3_REGION_NAME = "us-east-1"
AWS_QUERYSTRING_AUTH = False
AWS_DEFAULT_ACL = None

from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = "static"
    default_acl = "public-read"
    object_parameters = {"CacheControl": "max-age=31536000"}

class MediaStorage(S3Boto3Storage):
    location = "media"
    default_acl = "public-read"
    object_parameters = {"CacheControl": "max-age=60"}

STATICFILES_STORAGE = "ledger_api.settings.StaticStorage"
DEFAULT_FILE_STORAGE = "ledger_api.settings.MediaStorage"

STATIC_URL = "https://d3io7897jtegnn.cloudfront.net/static/"
MEDIA_URL = "https://d3io7897jtegnn.cloudfront.net/media/"

# ------------------------------------------------------------------------------
# SECURITY HEADERS (HARDCODED)
# ------------------------------------------------------------------------------
TENANT_MODEL = "customers.Client"
TENANT_DOMAIN_MODEL = "customers.Domain"
PUBLIC_SCHEMA_URLCONF = "customers.urls"

TENANT_COOKIE_DOMAIN = ".api.pekinledger.com"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = False  # change to true for production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"

# ------------------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
