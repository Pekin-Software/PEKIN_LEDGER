from pathlib import Path
import os
import dj_database_url
import logging

# optional: decouple if other parts rely on it
try:
    from decouple import config
except Exception:
    config = None

logger = logging.getLogger(__name__)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------
# Security / Core Settings
# --------------------------------------------------------------------
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-_!gb#a3e10(y9ur98k1h(pc2(w&+2*+v+jj*86s#lj2#)$xb86"
)

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledger_api.settings")

# --------------------------------------------------------------------
# Application definition
# --------------------------------------------------------------------
SHARED_APPS = [
    'django_tenants',
    'customers',
    'django_extensions',
    # 'django_hosts',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    "corsheaders",
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

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'customers.authentication.TenantAwareJWTAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'EXCEPTION_HANDLER': 'customers.exceptions.custom_exception_handler'
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY, 
}

MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ledger_api.urls'

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://testing022.client1.localhost:8000",
    "https://pekingledger.store",
    "https://app.pekingledger.store",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.pekingledger\.store$",
    r"^https://pekingledger\.store$",
]

CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ledger_api.wsgi.application'

# --------------------------------------------------------------------
# AWS S3 Storage
# --------------------------------------------------------------------
USE_AWS_STORAGE = os.getenv("USE_AWS_STORAGE", "False").lower() in ("true", "1", "yes")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "ledger-static-media")

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

if USE_AWS_STORAGE and not DEBUG:
    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_S3_CUSTOM_DOMAIN = os.getenv(
        "AWS_S3_CUSTOM_DOMAIN",
        f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
    )
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
else:
    STATIC_URL = '/static/'
    STATIC_ROOT = BASE_DIR / 'staticfiles'
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'


# --------------------------------------------------------------------
# Database + AWS Secrets Manager
# --------------------------------------------------------------------
# DATABASES = {
#     'default': {
#         'ENGINE': 'django_tenants.postgresql_backend',  
#         'NAME': 'pekin_ledger_db',
#         'USER': 'pekin',
#         'PASSWORD': 'ledger@2025',
#         'HOST': 'localhost', 
#         'PORT': '5432',
#     }
# }

# try:
#     import boto3, json
#     client = boto3.client("secretsmanager", region_name=AWS_S3_REGION_NAME)
#     response = client.get_secret_value(SecretId="LedgerBD-Credentials")
#     secrets = json.loads(response["SecretString"])

#     DATABASES["default"].update({
#         "NAME": secrets.get("dbname", DATABASES["default"]["NAME"]),
#         "USER": secrets.get("username", DATABASES["default"]["USER"]),
#         "PASSWORD": secrets.get("password", DATABASES["default"]["PASSWORD"]),
#         "HOST": secrets.get("host", DATABASES["default"]["HOST"]),
#         "PORT": secrets.get("port", DATABASES["default"]["PORT"]),
#     })
# except Exception as e:
#     logger.warning("Secrets Manager not available, using default DB settings: %s", e)

import os
import logging
import json

import boto3

logger = logging.getLogger(__name__)

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',  
        'NAME': 'pekin_ledger_db',
        'USER': 'pekin',
        'PASSWORD': 'ledger@2025',
        'HOST': 'localhost', 
        'PORT': '5432',
    }
}

# Use AWS Secrets Manager only if this env var is set to True
USE_SECRETS_MANAGER = os.getenv("USE_SECRETS_MANAGER", "False").lower() in ("true", "1", "yes")

if USE_SECRETS_MANAGER:
    try:
        AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "us-east-1")
        client = boto3.client("secretsmanager", region_name=AWS_S3_REGION_NAME)
        response = client.get_secret_value(SecretId="LedgerBD-Credentials")
        secrets = json.loads(response["SecretString"])

        DATABASES["default"].update({
            "NAME": secrets.get("dbname", DATABASES["default"]["NAME"]),
            "USER": secrets.get("username", DATABASES["default"]["USER"]),
            "PASSWORD": secrets.get("password", DATABASES["default"]["PASSWORD"]),
            "HOST": secrets.get("host", DATABASES["default"]["HOST"]),
            "PORT": secrets.get("port", DATABASES["default"]["PORT"]),
        })
        logger.info("Using Secrets Manager DB credentials.")
    except Exception as e:
        logger.warning("Secrets Manager not available, using default DB settings: %s", e)
else:
    logger.info("Using local DB settings.")


DATABASE_ROUTERS = (
   'django_tenants.routers.TenantSyncRouter',
)

# --------------------------------------------------------------------
# Authentication / Internationalization
# --------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = 'customers.User'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------
# Defaults
# --------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
TENANT_MODEL = "customers.Client"
TENANT_DOMAIN_MODEL = "customers.Domain"
PUBLIC_SCHEMA_URLCONF = 'customers.urls'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}
