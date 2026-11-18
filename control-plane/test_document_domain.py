"""Private PDF boundary: encryption, scan gate, approval and tenant access."""

from __future__ import annotations

import base64
import importlib.util
import sys
import socket
import struct
import threading
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent))
spec = importlib.util.spec_from_file_location("account_service_docs", Path(__file__).with_name("account_service.py"))
assert spec and spec.loader
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
from commercial_domain import simple_pdf
from document_domain import scanner_clean


def login(client, email, password):
    response = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_document_vault_requires_scanner_outside_evaluation(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    monkeypatch.delenv("ACCOUNT_CLAMD_HOST", raising=False)
    monkeypatch.setenv("ACCOUNT_DOCUMENT_KEY", Fernet.generate_key().decode())
    app = service.create_app(str(tmp_path / "prod.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = login(client, "root@example.test", "root-password-123")
    client.post("/v1/vendor/organizations", headers=root, json={"organization_id": "hospital-a", "name": "Hospital A"})
    pdf = simple_pdf(["Non-clinical contract test"])
    payload = {"organization_id": "hospital-a", "document_key": "contract-001", "version": 1, "title": "Test agreement", "document_type": "agreement", "access": "customer_visible", "owner_role": "Finance", "content_b64": base64.b64encode(pdf).decode()}
    assert client.post("/v1/vendor/documents", headers=root, json=payload).status_code == 503
    assert client.get("/v1/documents", headers=root).json()["documents"] == []


def test_synthetic_document_is_encrypted_and_tenant_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv("EVALUATION_RUNTIME", "true")
    monkeypatch.setenv("EVALUATION_ACCOUNT_PASSWORD", "evaluation-secret-123")
    monkeypatch.setenv("ACCOUNT_DOCUMENT_KEY", Fernet.generate_key().decode())
    app = service.create_app(str(tmp_path / "eval.db"))
    client = TestClient(app)
    evaluator = login(client, "evaluator@auralis.invalid", "evaluation-secret-123")
    assert client.post("/v1/vendor/customers", headers=evaluator, json={"organization_id": "evaluation-hospital", "email": "customer@example.test", "display_name": "Customer", "password": "customer-password-123"}).status_code == 200
    customer = login(client, "customer@example.test", "customer-password-123")
    # Even a second customer identity in this sandbox must only receive its own
    # organization's approved documents; evaluation cannot create production orgs.
    assert client.post("/v1/vendor/organizations", headers=evaluator, json={"organization_id": "other-hospital", "name": "Other hospital"}).status_code == 403
    pdf = simple_pdf(["Synthetic commercial document"])
    payload = {"organization_id": "evaluation-hospital", "site_id": "evaluation-icu", "document_key": "eval-contract", "version": 1, "title": "Evaluation agreement", "document_type": "agreement", "access": "customer_visible", "owner_role": "Finance", "content_b64": base64.b64encode(pdf).decode()}
    uploaded = client.post("/v1/vendor/documents", headers=evaluator, json=payload)
    assert uploaded.status_code == 200, uploaded.text
    assert client.post("/v1/vendor/documents", headers=evaluator, json=payload).status_code == 409
    document_id = uploaded.json()["id"]
    encrypted = app.state.store.db.execute("SELECT encrypted_pdf FROM documents WHERE id=?", (document_id,)).fetchone()[0]
    assert pdf not in encrypted
    assert client.get("/v1/documents", headers=customer).json()["documents"] == []
    assert client.get(f"/v1/documents/{document_id}/download", headers=customer).status_code == 404
    assert client.patch(f"/v1/vendor/documents/{document_id}", headers=evaluator, json={"reason": "Synthetic approval"}).status_code == 200
    assert len(client.get("/v1/documents", headers=customer).json()["documents"]) == 1
    downloaded = client.get(f"/v1/documents/{document_id}/download", headers=customer)
    assert downloaded.status_code == 200 and downloaded.content == pdf
    assert app.state.store.audit_integrity() is True


def test_approved_document_stays_with_its_customer(tmp_path, monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    monkeypatch.setenv("ACCOUNT_DOCUMENT_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr("document_domain.scanner_clean", lambda _: True)
    app = service.create_app(str(tmp_path / "accounts.db"))
    app.state.store.create_vendor("root@example.test", "Root", "root-password-123")
    client = TestClient(app)
    root = login(client, "root@example.test", "root-password-123")
    for suffix in ("a", "b"):
        client.post("/v1/vendor/organizations", headers=root, json={"organization_id": f"hospital-{suffix}", "name": f"Hospital {suffix.upper()}"})
        client.post("/v1/vendor/customers", headers=root, json={"organization_id": f"hospital-{suffix}", "email": f"customer-{suffix}@example.test", "display_name": "Customer", "password": "customer-password-123"})
    a = login(client, "customer-a@example.test", "customer-password-123")
    b = login(client, "customer-b@example.test", "customer-password-123")
    pdf = simple_pdf(["Hospital A document"])
    payload = {"organization_id": "hospital-a", "document_key": "agreement-a", "version": 1, "title": "Agreement A", "document_type": "agreement", "access": "customer_visible", "owner_role": "Finance", "content_b64": base64.b64encode(pdf).decode()}
    uploaded = client.post("/v1/vendor/documents", headers=root, json=payload)
    assert uploaded.status_code == 200, uploaded.text
    document_id = uploaded.json()["id"]
    assert client.patch(f"/v1/vendor/documents/{document_id}", headers=root, json={"reason": "Approved for customer A"}).status_code == 200
    assert client.get(f"/v1/documents/{document_id}/download", headers=a).status_code == 200
    assert client.get(f"/v1/documents/{document_id}/download", headers=b).status_code == 404
    assert client.get("/v1/documents", headers=b).json()["documents"] == []
    viewer = client.post("/v1/vendor/customers", headers=root, json={"organization_id": "hospital-a", "email": "viewer@example.test", "display_name": "Training viewer", "password": "viewer-password-123", "role": "customer_viewer"})
    assert viewer.status_code == 200
    viewer_token = login(client, "viewer@example.test", "viewer-password-123")
    assert client.get("/v1/documents", headers=viewer_token).json()["documents"] == []
    assert client.get(f"/v1/documents/{document_id}/download", headers=viewer_token).status_code == 404
    training_payload = {**payload, "document_key": "training-a", "document_type": "training", "title": "Training record"}
    training_upload = client.post("/v1/vendor/documents", headers=root, json=training_payload)
    assert training_upload.status_code == 200
    training_id = training_upload.json()["id"]
    assert client.patch(f"/v1/vendor/documents/{training_id}", headers=root, json={"reason": "Approved training record"}).status_code == 200
    assert [row["id"] for row in client.get("/v1/documents", headers=viewer_token).json()["documents"]] == [training_id]
    assert client.get(f"/v1/documents/{training_id}/download", headers=viewer_token).status_code == 200


def test_clamd_stream_protocol_and_infected_rejection(monkeypatch):
    monkeypatch.delenv("EVALUATION_RUNTIME", raising=False)
    payload = simple_pdf(["Scanner protocol test"])
    for answer, expected in ((b"stream: OK\0", True), (b"stream: Test-Signature FOUND\0", False)):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        monkeypatch.setenv("ACCOUNT_CLAMD_HOST", "127.0.0.1")
        monkeypatch.setenv("ACCOUNT_CLAMD_PORT", str(listener.getsockname()[1]))
        def serve():
            with listener:
                connection, _ = listener.accept()
                with connection:
                    assert connection.recv(10) == b"zINSTREAM\0"
                    size = struct.unpack(">I", connection.recv(4))[0]
                    received = bytearray()
                    while len(received) < size:
                        received.extend(connection.recv(size - len(received)))
                    assert bytes(received) == payload
                    assert connection.recv(4) == b"\x00\x00\x00\x00"
                    connection.sendall(answer)
        worker = threading.Thread(target=serve)
        worker.start()
        assert scanner_clean(payload) is expected
        worker.join(timeout=2)
        assert not worker.is_alive()
