from pathlib import Path
import os
import dj_database_url
from decouple import config
from urllib.parse import urlparse

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY = 'django-insecure-_!gb#a3e10(y9ur98k1h(pc2(w&+2*+v+jj*86s#lj2#)$xb86'

SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-secret-for-dev")

# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG = False
# DEBUG = config('DEBUG', default=False, cast=bool)
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
# ALLOWED_HOSTS = ["https://pekin-ledger.onrender.com", ]
# ALLOWED_HOSTS = [
#     ".pekingledger.store",
#     "pekingledger.store", 
#     "localhost", 
#     ".localhost"
#     ]

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*.api.pekinledger.com,*.elasticbeanstalk.com").split(",")
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS if host]


# Application definition
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
    'storages',
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
    # 'django_hosts.middleware.HostsResponseMiddleware',
]

ROOT_URLCONF = 'ledger_api.urls'

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    # "http://localhost:5173",
    # "http://testing022.client1.localhost:8000",
    # "https://pekingledger.store",
    "https://app.pekingledger.com",
    "https://api.pekinledger.com",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
  r"^https:\/\/.*\.api\.pekinledger\.com$",
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

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

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

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get("DATABASE_URL"),
        engine="django_tenants.postgresql_backend",
    )
}

DATABASE_ROUTERS = (
   'django_tenants.routers.TenantSyncRouter',
)

# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#         }
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Default backend
]
AUTH_USER_MODEL = 'customers.User'


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

# STATIC_URL = 'static/'
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
AWS_STORAGE_BUCKET_NAME = os.environ.get('STATIC_S3_BUCKET', 'pekinledger-eb-deploy')
AWS_MEDIA_BUCKET_NAME = os.environ.get('MEDIA_S3_BUCKET', 'pekinledger-media')
AWS_S3_REGION_NAME = os.environ.get('AWS_REGION', 'us-east-1')

AWS_DEFAULT_ACL = None
AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}

STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/"
MEDIA_URL = f"https://{AWS_MEDIA_BUCKET_NAME}.s3.amazonaws.com/"

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TENANT_MODEL = "customers.Client"  # Define the tenant model

TENANT_DOMAIN_MODEL = "customers.Domain"  # Define the tenant domain model

PUBLIC_SCHEMA_URLCONF = 'customers.urls'

#cookies setting 
# Parent domain for all tenants (leading dot is important)
TENANT_COOKIE_DOMAIN = ".api.pekinledger.com"

# Use HTTPS in production, required for SameSite=None
SECURE_COOKIE = True  # set to False only in local/dev if necessary

# Optional: keep these aligned with your CSRF/CORS setup
CSRF_COOKIE_SECURE = SECURE_COOKIE
SESSION_COOKIE_SECURE = SECURE_COOKIE
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')