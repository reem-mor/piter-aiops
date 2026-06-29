"""Static dataset cache behavior."""
from __future__ import annotations

from app.services import data_access


def test_source_loaders_reuse_cache():
    data_access.reset_data_cache()
    first = data_access.load_service_owners()
    second = data_access.load_service_owners()
    assert first is second
    assert len(first) > 0


def test_reset_data_cache_reloads():
    data_access.reset_data_cache()
    first = data_access.load_business_impact()
    data_access.reset_data_cache()
    second = data_access.load_business_impact()
    assert first == second
    assert first is not second
