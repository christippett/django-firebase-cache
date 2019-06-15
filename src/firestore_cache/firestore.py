"Firestore cache backend"
import base64
import pickle
import re
from datetime import datetime
from typing import Iterable

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.utils import timezone
from google.cloud import firestore
from google.cloud.firestore import (
    CollectionReference,
    DocumentReference,
    DocumentSnapshot,
)


class FirestoreCache(BaseCache):
    pickle_protocol = pickle.HIGHEST_PROTOCOL

    def __init__(self, collection, params):
        super().__init__(params)
        self._collection_name = collection
        self._options = params.get("OPTIONS") or {}

    @property
    def _cache(self) -> CollectionReference:
        if getattr(self, "_collection", None) is None:
            client = firestore.Client(**self._options)
            self._collection = client.collection(self._collection_name)

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
            data = {"value": b64encoded, "expires": exp}
        doc: DocumentSnapshot = self._cache.document(key).get()
        doc.set(data, merge=True)

    def validate_key(self, key):
        if re.search(r"^__.*__$", key):
            return False
        elif re.search(r"^\.+$", key):
            return False
        elif re.search(r"\/", key):
            return False
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
        docs: Iterable[DocumentReference] = self._cache.list_documents()
        for doc_ref in docs:
            doc_ref.delete()
