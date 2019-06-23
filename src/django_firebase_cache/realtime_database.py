"Firestore cache backend"
import base64
import hashlib
import pickle
import re
import warnings
from datetime import datetime

import firebase_admin
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache, CacheKeyWarning
from firebase_admin import db
from firebase_admin.db import Reference

FIREBASE_APP = None


class RealtimeDatabaseCache(BaseCache):
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, cache_key, params):
        super().__init__(params)
        self.db_key = cache_key
        self._options = params.get("OPTIONS") or {}

    @property
    def db(self) -> Reference:
        if getattr(self, "_db", None) is None:
            global FIREBASE_APP
            if FIREBASE_APP is None:
                FIREBASE_APP = firebase_admin.initialize_app(
                    options=self._options, name="DJANGO_CACHE"
                )
            ref = db.reference(self.db_key, app=FIREBASE_APP)
            if self.key_prefix:
                ref = ref.child(self.key_prefix)
            self._db: Reference = ref

        return self._db

    def _set_data(self, mode, key, value, timeout=DEFAULT_TIMEOUT):
        timeout = self.get_backend_timeout(timeout)
        if timeout is None:
            exp = datetime.max
        else:
            exp = datetime.utcfromtimestamp(timeout)
        exp = exp.replace(microsecond=0)

        pickled = pickle.dumps(value, self.pickle_protocol)
        b64encoded = base64.b64encode(pickled).decode("utf-8")
        if mode == "touch":
            data = {"expires": exp}
        else:
            data = {"cache_key": key, "value": b64encoded, "expires": exp.timestamp()}
        return data

    def make_key(self, key, version=None):
        key = super().make_key(key, version)
        md5_key = hashlib.md5(key.encode("utf-8")).hexdigest()
        return md5_key

    def validate_key(self, key):
        if re.search(r"[\.\$\#\[\]\/\n]", key):
            warnings.warn(
                "Keys used with Firebase Realtime Database must be UTF-8 "
                "encoded and can't contain new lines or any of the "
                "following characters: . $ # [ ] / or any ASCII control "
                "characters (0x00 - 0x1F and 0x7F): %r" % key,
                CacheKeyWarning,
            )
        super().validate_key(key)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        og_key = key
        key = self.make_key(key, version=version)
        self.validate_key(key)
        data = self._set_data("add", og_key, value, timeout)
        self.db.child(key).set(data)

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        data = self.db.child(key).get()
        if data:
            expires = datetime.utcfromtimestamp(data.get("expires", 0))
            if expires >= datetime.utcnow():
                value = data.get("value")
                return pickle.loads(base64.b64decode(value.encode()))
            else:
                self.delete(key, version)
        return default

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        og_key = key
        key = self.make_key(key, version=version)
        self.validate_key(key)
        data = self._set_data("set", og_key, value, timeout)
        self.db.child(key).set(data)

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        set_data = {}
        for key, value in data.items():
            og_key = key
            key = self.make_key(key, version=version)
            set_data[key] = self._set_data("set", og_key, value, timeout)
        self.db.set(set_data)
        return []

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        og_key = key
        key = self.make_key(key, version=version)
        self.validate_key(key)
        data = self._set_data("touch", og_key, None, timeout)
        self.db.child(key).update(data)

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        self.db.child(key).delete

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        doc = self.db.child(key).get()
        return doc is not None

    def clear(self):
        self.db.delete()
