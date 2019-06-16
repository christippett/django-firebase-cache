"Firestore cache backend"
import base64
import pickle
import re
import warnings
from datetime import datetime
from typing import Iterable

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache, CacheKeyWarning
from django.utils import timezone
from google.cloud import firestore
from google.cloud.firestore import (
    CollectionReference,
    DocumentReference,
    DocumentSnapshot,
)


class FirestoreCache(BaseCache):
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, cache_key, params):
        super().__init__(params)
        self._cache_key = cache_key
        self._options = params.get("OPTIONS") or {}
        self.key_prefix = self.key_prefix or "django"

    @property
    def _cache(self) -> CollectionReference:
        if getattr(self, "_collection", None) is None:
            service_account = self._options.get("service_account", None)
            firestore_options = self._options.get("firestore_options", {})
            if service_account:
                client = firestore.Client.from_service_account_json(
                    service_account, **firestore_options
                )
            else:
                client = firestore.Client(**self._options)
            ref = client.collection(self._cache_key)
            self._collection: CollectionReference = ref

        return self._collection

    def _base_set(self, mode, key, value, timeout=DEFAULT_TIMEOUT):
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
            data = {"value": b64encoded, "expires": exp, "key_prefix": self.key_prefix}
        doc_ref: DocumentReference = self._cache.document(key)
        doc_ref.set(data, merge=True)

    def validate_key(self, key):
        if re.search(r"^__.*__$", key):
            warnings.warn(
                "Keys used with Cloud Firestore "
                "cannot match the regular expression __.*__: %r" % key,
                CacheKeyWarning,
            )
        elif re.search(r"^\.+$", key):
            warnings.warn(
                "Keys used with Cloud Firestore "
                "cannot solely consist of a single period (.) "
                "or double periods (..): %r" % key,
                CacheKeyWarning,
            )
        elif re.search(r"\/", key):
            warnings.warn(
                "Keys used with Cloud Firestore "
                "cannot contain a forward slash (/): %r" % key,
                CacheKeyWarning,
            )
        return super().validate_key(key)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set("add", key, value, timeout)

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        doc: DocumentSnapshot = self._cache.document(key).get()
        if not doc.exists:
            return default
        data = doc.to_dict()
        expires = data.get("expires")
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
        self._base_set("set", key, value, timeout)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return self._base_set("touch", key, None, timeout)

    def delete(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        doc_ref: DocumentReference = self._cache.document(key)
        doc_ref.delete()

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        doc: DocumentSnapshot = self._cache.document(key).get()
        return doc.exists

    def clear(self):
        docs: Iterable[DocumentSnapshot] = self._cache.where(
            "key_prefix", "==", self.key_prefix
        ).stream()
        for doc in docs:
            doc.reference.delete()
