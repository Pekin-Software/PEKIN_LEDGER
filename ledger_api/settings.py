from pathlib import Path
import os
import dj_database_url
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-_!gb#a3e10(y9ur98k1h(pc2(w&+2*+v+jj*86s#lj2#)$xb86'

DEBUG = False

ALLOWED_HOSTS = [
    "api.pekinledger.com",
    "*.api.pekinledger.com", 
    "localhost", 
    ".localhost"
]

SHARED_APPS = [
    'django_tenants',
    'customers',
    'django_extensions',
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
    "storages",
]

INSTALLED_APPS = SHARED_APPS + [app for app in TENANT_APPS if app not in SHARED_APPS]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'customers.authentication.TenantAwareJWTAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'EXCEPTION_HANDLER': 'customers.exceptions.custom_exception_handler'
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
    "https://pekinledger.com",
    "https://app.pekinledger.com",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.pekinledger\.com$",
    r"^https://pekinledger\.com$",
]

CORS_ALLOW_HEADERS = [
    "content-type",
    "authorization",
]

WSGI_APPLICATION = 'ledger_api.wsgi.application'

# --------------------------------------------------------------------
# Static and Media Files
# --------------------------------------------------------------------

# STATIC_URL = 'static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media'

AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = config("AWS_REGION", default="eu-west-3")
AWS_S3_ENDPOINT_URL = config("AWS_S3_ENDPOINT_URL", default=None)

STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/static/"
MEDIA_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com/media/"

# --------------------------------------------------------------------
# Database & Templates
# --------------------------------------------------------------------

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

# DATABASES = {
#     'default': {
#         'ENGINE': 'django_tenants.postgresql_backend',  
#         'NAME': config("DB_NAME"),
#         'USER': config("DB_USER"),
#         'PASSWORD': config("DB_PASSWORD"),
#         'HOST': config("DB_HOST"),
#         'PORT': config("DB_PORT", default="5432"),
#     }
# }


# DATABASES = {
#     'default': dj_database_url.config(
#         default=config('DATABASE_URL'),
#         conn_max_age=600,
#         engine='django_tenants.postgresql_backend'
#     )
# }


DATABASE_ROUTERS = (
   'django_tenants.routers.TenantSyncRouter',
)

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


# -------------------------------------------------------------------
# Authentication / Internationalization
# -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
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

