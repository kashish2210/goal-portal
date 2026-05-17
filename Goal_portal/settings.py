"""
Django settings for Goal_portal project.
Reads config from environment variables (via .env for local, Render env vars for production).
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# ── Base ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file when running locally (no-op on Render where vars are injected)
load_dotenv(BASE_DIR / '.env')

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-2wac3vfi@8#pzfzg3dhobr3smjsmfcdc)e6h7hanb^-+frb!us'
)

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS_ENV = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_ENV.split(',') if h.strip()] or ['*']

# ── Application definition ────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'goals',
    'dashboards',
    'reports',
    'portal',
    'manager',
    'accounts',
    'integrations',
]

# ── Email (5.2) ───────────────────────────────────────────────────────────────
# Override in .env / production settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # swap to smtp in prod
DEFAULT_FROM_EMAIL = 'goaltrack@yourorg.com'

# ── Microsoft Teams webhook (5.2) ─────────────────────────────────────────────
# TEAMS_WEBHOOK_URL = 'https://outlook.office.com/webhook/...'

# ── Site base URL for deep links (5.2 / 5.3) ─────────────────────────────────
# SITE_BASE_URL = 'https://your-domain.com'

# ── Azure AD / Entra ID SSO (5.1) ────────────────────────────────────────────
# AZURE_AD_CLIENT_ID     = '<app-client-id>'
# AZURE_AD_CLIENT_SECRET = '<client-secret>'
# AZURE_AD_TENANT_ID     = '<tenant-id>'
# AZURE_AD_REDIRECT_URI  = 'https://your-domain.com/integrations/azure/callback/'
# AZURE_AD_ROLE_MAP = {
#     '<admin-group-object-id>':    'admin',
#     '<manager-group-object-id>':  'manager',
#     '<employee-group-object-id>': 'employee',
# }

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',          # ← Serve static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Goal_portal.urls'

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

WSGI_APPLICATION = 'Goal_portal.wsgi.application'

# ── Database ──────────────────────────────────────────────────────────────────
_DATABASE_URL = os.environ.get('DATABASE_URL', '')

if _DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            _DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback to SQLite for local development without DATABASE_URL set
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Password validation ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise: serve compressed, forever-cacheable static files
STORAGES = {
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# ── Auth ──────────────────────────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'goals.User'
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = 'accounts:login'

# ── Production security headers (only when DEBUG=False) ───────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    CSRF_TRUSTED_ORIGINS = [
        f"https://{h.strip()}"
        for h in ALLOWED_HOSTS_ENV.split(',')
        if h.strip() and not h.strip().startswith('*')
    ]
