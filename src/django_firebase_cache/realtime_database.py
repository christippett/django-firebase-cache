"Firestore cache backend"
import base64
import pickle
import re
import warnings
from datetime import datetime

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache, CacheKeyWarning
from django.utils import timezone
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin.db import Reference


class RealtimeDatabaseCache(BaseCache):
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, cache_key, params):
        super().__init__(params)
        self._cache_key = cache_key
        self._options = params.get("OPTIONS") or {}

    @property
    def _cache(self) -> Reference:
        if getattr(self, "_ref", None) is None:
            cred = None
            service_account = self._options.get("service_account", None)
            firebase_options = self._options.get("firebase_options", {})
            if service_account:
                cred = credentials.Certificate(service_account)
            firebase_admin.initialize_app(
                credential=cred, options=firebase_options, name="DJANGO_CACHE"
            )
            ref = db.reference(self._cache_key)
            if self.key_prefix:
                ref = ref.child(self.key_prefix)
            self._ref: Reference

        return self._ref

    def _set_data(self, mode, value, timeout=DEFAULT_TIMEOUT):
        if timeout is None:
            exp = datetime.max
        elif settings.USE_TZ:
            exp = datetime.utcfromtimestamp(timeout)
        else:
            exp = datetime.fromtimestamp(timeout)
        exp = exp.replace(microsecond=0)

        pickled = pickle.dumps(value, self.pickle_protocol)
        b64encoded = base64.b64encode(pickled).decode("utf-8")
        if mode == "touch":
            data = {"expires": exp}
        else:
            data = {"value": b64encoded, "expires": exp.timestamp()}
        return data

    def validate_key(self, key):
        if re.search(r"[\.\$\#\[\]\/\n]", key):
            warnings.warn(
                "Keys used with Firebase Realtime Database must be UTF-8 "
                "encoded and can't contain new lines or any of the "
                "following characters: . $ # [ ] / or any ASCII control "
                "characters (0x00 - 0x1F and 0x7F: %r" % key,
                CacheKeyWarning,
            )
        super().validate_key(key)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        data = self._set_data("add", None, timeout)
        self._cache.key(key).set(data)

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        data = self._cache.child(key).get()
        expires = datetime.fromtimestamp(data.get("expires", 0))
        if expires >= timezone.now():
            value = data.get("value")
            value = pickle.loads(base64.b64decode(value.encode()))
            return value
        else:
            self.delete(key, version)
            return default

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        data = self._set_data("set", None, timeout)
        self._cache.key(key).set(data)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        set_data = {}
        for key, value in data.items():
            key = self.make_key(key, version=version)
            set_data[key] = self._set_data("set", value, timeout)
        self._cache.set(set_data)
        return []

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        data = self._set_data("touch", None, timeout)
        self._cache.key(key).update(data)

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        self._cache.child(key).delete

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        doc = self._cache.child(key).get()
        return doc is not None

    def clear(self):
        self._cache.delete()
