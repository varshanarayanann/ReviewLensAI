def test_every_application_api_route_requires_auth(client):
    """New operations must reject anonymous callers without leaking data."""
    public = {"/api/health", "/api/health/db"}
    protected = []
    for path, operations in client.app.openapi()["paths"].items():
        if not path.startswith("/api/") or path in public:
            continue
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            protected.append((method, path))
            assert operation.get("security"), (method, path)
            response = client.request(method.upper(), path)
            assert response.status_code == 401, (method, path, response.text)
            assert response.json() == {"detail": "Authentication required."}
    assert protected
