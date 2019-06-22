"Firestore cache backend"
import base64
import pickle
import re
import warnings
from datetime import datetime
from typing import Iterable

from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache, CacheKeyWarning
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
        self._collection = collection
        self._options = params.get("OPTIONS") or {}

    @property
    def db(self) -> CollectionReference:
        if getattr(self, "_db", None) is None:
            client = firestore.Client(**self._options)
            ref = client.collection(self._collection)
            self._db: CollectionReference = ref

        return self._db

    def _base_set(self, mode, key, value, timeout=DEFAULT_TIMEOUT):
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
            data = {"value": b64encoded, "expires": exp, "key_prefix": self.key_prefix}
        doc_ref: DocumentReference = self.db.document(key)
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
        doc: DocumentSnapshot = self.db.document(key).get()
        if not doc.exists:
            return default
        data = doc.to_dict()
        expires = data.get("expires")
        if expires >= datetime.utcnow():
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
        doc_ref: DocumentReference = self.db.document(key)
        doc_ref.delete()

    def has_key(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        doc: DocumentSnapshot = self.db.document(key).get()
        return doc.exists

    def clear(self):
        docs: Iterable[DocumentSnapshot] = self.db.where(
            "key_prefix", "==", self.key_prefix
        ).stream()
        for doc in docs:
            doc.reference.delete()
