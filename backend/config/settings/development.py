from .base import *
from decouple import config

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# In dev: allow all origins to prevent CORS errors with dynamic Vite dev server ports (e.g., 5175)
CORS_ALLOW_ALL_ORIGINS = True

# Show DRF's browsable API in dev only
REST_FRAMEWORK = {
    **globals().get("REST_FRAMEWORK", {}),
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}
