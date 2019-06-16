import os
import pytest

from mockfirestore import MockFirestore
from google.cloud import firestore
from django.core.cache import cache

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "firestore_settings")


@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(firestore, "Client", MockFirestore)
        yield


def test_can_write_to_cache(mock_db):
    cache.add(key="key123", value="value123", timeout=None)
    assert cache.get("key123") == "value123"
