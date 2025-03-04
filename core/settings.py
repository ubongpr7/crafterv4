import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-$*r+l*b2dxn-j-rk=r57ejwy575^g_x^+ac9a2jc&&w$&99mc&"

DEBUG = True

ALLOWED_HOSTS = ["*"]

DEFAULT_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "bootstrap5",
    "django_htmx",
    "storages",
    # "django_crontab"
]

MAIN_APPS = [
    "mainapps.video",
    "mainapps.home",
    "mainapps.accounts",
    "mainapps.vidoe_text",
    "mainapps.audio",
]

INSTALLED_APPS = []
INSTALLED_APPS.extend(DEFAULT_APPS)
INSTALLED_APPS.extend(THIRD_PARTY_APPS)
INSTALLED_APPS.extend(MAIN_APPS)

CRONJOBS = [
    ('*/5 * * * *', 'mainapps.vidoe_text.tasks.delete_old_textfiles_job.delete_od_files'),
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_NAME"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD":  os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": "5432",
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 6,
        },
    },
]

LANGUAGE_CODE = "en-us"
USE_I18N = True
TIME_ZONE = "UTC"
USE_TZ = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.office365.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DOMAIN_NAME =  os.getenv("DOMAIN_NAME")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATIC_URL = "static/" 
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

MEDIA_URL = "media/" 
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
    
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME')
AWS_S3_CUSTOM_DOMAIN = "%s.s3.amazonaws.com" % AWS_STORAGE_BUCKET_NAME
AWS_S3_FILES_OVERWRITE = False
AWS_S3_CONNECT_TIMEOUT = 10  
AWS_S3_TIMEOUT = 60 
AWS_S3_FILE_OVERWRITE=True


STORAGES = {
        "default": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
        "staticfiles": {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"},
}

PASSWORD_RESET_TIMEOUT = 3600 * 24

GROWTH_PLAN_PRICE_ID = os.getenv('GROWTH_PLAN_PRICE_ID')
PRO_PLAN_PRICE_ID =  os.getenv('PRO_PLAN_PRICE_ID')

STRIPE_PUP_KEY = os.getenv('STRIPE_PUP_KEY')
STRIPE_SEC_KEY = os.getenv('STRIPE_SEC_KEY')
STRIPE_ENDPOINT_SECRET = os.getenv('STRIPE_ENDPOINT_SECRET')
CLOUDCONVERT_API_KEY=os.getenv('CLOUDCONVERT_API_KEY')


SESSION_COOKIE_SECURE=False
SECURE_CROSS_ORIGIN_OPENER_POLICY = None