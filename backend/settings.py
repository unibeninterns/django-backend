from datetime import timedelta
from pathlib import Path
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', '.ngrok-free.dev']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'channels',

    'django.contrib.sites', 

    # App
    'users',
    'module',
    'progresse',
    'payments',
    'assessments',
    'finance',

    # REST Framework & Auth
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'rest_framework.authtoken',

    #swagger
    'drf_yasg',

    # CORS
    'corsheaders',

    #Celery Beat
    'django_celery_beat',
    'django_celery_results',

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

FLUTTERWAVE_SECRET_KEY = os.getenv('FLUTTERWAVE_SECRET_KEY')
FLUTTERWAVE_PUBLIC_KEY = os.getenv('FLUTTERWAVE_PUBLIC_KEY')
FLUTTERWAVE_SECRET_HASH = os.getenv('FLUTTERWAVE_SECRET_HASH')

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
        # 'rest_framework.authentication.SessionAuthentication',
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
SOCIALACCOUNT_ADAPTER = 'users.adapters.CustomSocialAccountAdapter'

# Frontend URL
FRONTEND_URL = "http://127.0.0.1:8000"   #Vite Endpoint, please change as expected

SITE_URL = "http://127.0.0.1:8000" 

# dj-rest-auth custom serializer
REST_AUTH = {
    'USE_JWT': True,
    'SESSION_LOGIN': False,
    'JWT_AUTH_HTTPONLY': False,
    'REGISTER_SERIALIZER': 'users.serializers.CustomRegisterSerializer',
    'LOGIN_SERIALIZER': 'users.serializers.CustomLoginSerializer',
    'PASSWORD_RESET_CONFIRM_URL': f'{FRONTEND_URL}/reset-password/{{uid}}/{{token}}/',
    'OLD_PASSWORD_FIELD_ENABLED': True,
    'PASSWORD_RESET_SERIALIZER': 'dj_rest_auth.serializers.PasswordResetSerializer',
}

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('SMTP_HOST')
EMAIL_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_HOST_USER = os.getenv('SMTP_USER')
EMAIL_HOST_PASSWORD = os.getenv('SMTP_PASS')
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
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


# Celery Configuration

# This tells Django to use the Channels routing system for WebSockets
ASGI_APPLICATION = 'backend.asgi.application'

# This is the "bus" that lets Django and Celery talk to each other
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

CELERY_TIMEZONE = 'UTC'
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'django-db'  #this stores the celery response to the database

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'daily-aggregation': {
        'task': 'finance.tasks.aggregate_daily_metrics',
        'schedule': crontab(hour=0, minute=0),
    },
    'weekly-aggregation': {
        'task': 'yourapp.tasks.aggregate_weekly_metrics',
        'schedule': crontab(minute=0, hour=0, day_of_week='sun'),
    },
    'monthly-aggregation': {
        'task': 'yourapp.tasks.aggregate_monthly_metrics',
        'schedule': crontab(minute=0, hour=0, day_of_month='1'),
    },

}

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            # This links your .env variable to the Allauth configuration
            'client_id': os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY'),
            'secret': os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET'),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

# # Test Celery locally
# CELERY_BROKER_URL = 'memory://'
# CELERY_RESULT_BACKEND = 'cache+memory://'



