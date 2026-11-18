from app.api.routes.auth import _resolved_workspaces
from app.auth import Actor


def test_server_resolves_only_supported_workspaces():
    operator = _resolved_workspaces(Actor("vendor", "operator", "password"), "site-a")
    assert [item["id"] for item in operator["workspaces"]] == ["platform"]
    assert operator["default_path"] == "/platform/overview"
    assert operator["organization_id"] is None

    admin = _resolved_workspaces(Actor("admin", "admin", "password"), "site-a")
    assert [item["id"] for item in admin["workspaces"]] == ["hospital-admin", "clinical"]
    assert all(item["site_id"] == "site-a" for item in admin["workspaces"])

    nurse = _resolved_workspaces(Actor("nurse", "nurse", "password"), "site-a")
    assert nurse["default_path"] == "/app/chart"

    integration = _resolved_workspaces(Actor("connector", "integration", "integration-key"), "site-a")
    assert integration["workspaces"] == []
    assert integration["default_path"] is None

    integration_staff = _resolved_workspaces(Actor("engineer", "integration", "password"), "site-a")
    assert integration_staff["default_path"] == "/app/admin/integrations"
