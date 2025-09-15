from datetime import timedelta
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-fk5hmq=yg%4o%afyvk(8qc)96dpy6_&$obopb_*c$#q&5f9(4k'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',

    'django.contrib.sites', 

    # App
    'users',
    'module',
    'progresse',
    'payments',
    'assessments',

    # REST Framework & Auth
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'rest_framework.authtoken',

    #swagger
    'drf_yasg',

    # CORS
    'corsheaders',

    # Allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',

    # Social providers
    'allauth.socialaccount.providers.google',

    # dj-rest-auth
    'dj_rest_auth',
    'dj_rest_auth.registration',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
      'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
      'module.permissions': { 'handlers': ['console'], 'level': 'DEBUG' },
    }
}


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.CustomUser'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

REST_USE_JWT = True

# Allauth settings
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'first_name*', 'last_name*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True

# Frontend URL
FRONTEND_URL = "http://localhost:5173"   #Vite Endpoint, please change as expected 

SITE_URL = "http://127.0.0.1:8000" 


# dj-rest-auth custom serializer
REST_AUTH = {
    'REGISTER_SERIALIZER': 'users.serializers.CustomRegisterSerializer',
    'LOGIN_SERIALIZER': 'users.serializers.CustomLoginSerializer',
    'PASSWORD_RESET_CONFIRM_URL': f'{FRONTEND_URL}/reset-password/{{uid}}/{{token}}/',
    'OLD_PASSWORD_FIELD_ENABLED': True,
    'SIGNUP_FIELDS': {
            'username': {'required': False},
            'email': {'required': True},
        },
}

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('SMTP_HOST')
EMAIL_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_HOST_USER = os.getenv('SMTP_USER')
EMAIL_HOST_PASSWORD = os.getenv('SMTP_PASS')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_FROM')

# CORS settings
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        # we will add production
    ]

# Media files for development
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


