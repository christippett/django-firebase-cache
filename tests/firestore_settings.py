SECRET_KEY = "django_tests_secret_key"

CACHES = {
    "default": {
        "BACKEND": "django_firebase_cache.FirestoreCache",
        "LOCATION": "django",
    },
    "with_prefix": {
        "BACKEND": "django_firebase_cache.FirestoreCache",
        "LOCATION": "django",
        "KEY_PREFIX": "test-prefix",
    },
}

INSTALLED_APPS = ("django.contrib.sessions",)
