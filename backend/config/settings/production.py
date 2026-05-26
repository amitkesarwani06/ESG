from .base import *
from decouple import config

DEBUG = False

# Allow Railway domain
ALLOWED_HOSTS = [
    "*"
]

# Frontend URL for CORS
CORS_ALLOWED_ORIGINS = [
    "https://esg-frontend-production-d25a.up.railway.app",
]

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    "https://esg-frontend-production-d25a.up.railway.app",
    "https://esg-backend-production-73d1.up.railway.app",
    "https://*.up.railway.app",
]

# HTTPS settings
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Optional
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SAMESITE = "None"