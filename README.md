# Django Firebase Cache
[![PyPI version](https://img.shields.io/pypi/v/django-firebase-cache.svg)](https://pypi.python.org/pypi/django-firebase-cache)
[![Build status](https://img.shields.io/travis/christippett/django-firebase-cache.svg)](https://travis-ci.org/christippett/django-firebase-cache)
[![Coverage](https://img.shields.io/coveralls/github/christippett/django-firebase-cache.svg)](https://coveralls.io/github/christippett/django-firebase-cache?branch=master)
[![Python versions](https://img.shields.io/pypi/pyversions/django-firebase-cache.svg)](https://pypi.python.org/pypi/django-firebase-cache)
[![Github license](https://img.shields.io/github/license/christippett/django-firebase-cache.svg)](https://github.com/christippett/django-firebase-cache)

## Install
```bash
pip install django-firebase-cache
```

## Usage
```python
# settings.py

CACHES = {
    "firebase": {
        "BACKEND": "django_firebase_cache.RealtimeDatabaseCache",
        "LOCATION": "django",  # name of child key in Realtime Database
        "OPTIONS": {"databaseURL": "https://project-id.firebaseio.com/"},
    },
    "firestore": {
        "BACKEND": "django_firebase_cache.FirestoreCache",
        "LOCATION": "django",  # name of collection in Firestore
    },
}
```