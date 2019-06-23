import os
import pytest

from mockfirestore import MockFirestore
from google.cloud import firestore
from django.core.cache import cache
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "firestore_settings")


DEFAULT_CACHE_LOCATION = settings.CACHES["default"]["LOCATION"]

mock_firestore = MockFirestore()


@pytest.fixture(autouse=True)
def db(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(firestore, "Client", lambda: mock_firestore)
        yield mock_firestore
        mock_firestore.reset()
        cache._db = None  # reset cached Firestore client


def test_can_write_to_cache(db):
    cache.add(key="key1", value="value1", timeout=None)
    doc_refs = db.collection(DEFAULT_CACHE_LOCATION).list_documents()
    assert cache.get("key1") == "value1"
    assert len(doc_refs) == 1


def test_can_write_multiple_keys_to_cache(db):
    cache.add(key="key1", value="value1", timeout=None)
    cache.add(key="key2", value="value2", timeout=None)
    doc_refs = db.collection(DEFAULT_CACHE_LOCATION).list_documents()
    assert len(doc_refs) == 2
