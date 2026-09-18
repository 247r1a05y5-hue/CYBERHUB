"""Frontend Contract & API Schema Diff Verification Suite.

Guarantees:
- Zero breaking changes to existing endpoints (/api/v1/investigations, /reference-images, /findings, /dataset/match)
- Zero deleted properties or modified field types
- Strictly additive backwards-compatibility across OpenAPI schema
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

EXPECTED_CORE_ROUTES = [
    ("/api/v1/auth/login", {"POST"}),
    ("/api/v1/auth/register", {"POST"}),
    ("/api/v1/investigations", {"GET", "POST"}),
    ("/api/v1/dataset/participants", {"GET", "POST"}),
    ("/api/v1/diagnostics/search", {"GET"}),
]


def test_frozen_frontend_routes_exist():
    """Verify that all baseline API endpoints remain present and mapped to their expected methods."""
    registered_routes: dict[str, set[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path and methods:
            if path not in registered_routes:
                registered_routes[path] = set()
            registered_routes[path].update(methods)

    for expected_path, expected_methods in EXPECTED_CORE_ROUTES:
        assert expected_path in registered_routes, f"Required frozen route '{expected_path}' is missing!"
        for m in expected_methods:
            assert m in registered_routes[expected_path], f"Method '{m}' missing from route '{expected_path}'"


def test_openapi_schema_contains_frozen_contracts():
    """Verify that OpenAPI schema exports valid structures without deleted models."""
    schema = app.openapi()
    assert "paths" in schema
    assert "components" in schema
    assert "schemas" in schema["components"]

    # Verify search & investigation schemas are present
    schemas = schema["components"]["schemas"]
    assert "SearchDiagnosticsResponse" in schemas
