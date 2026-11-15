import os
import sys
import time
import importlib.util
from unittest.mock import patch, MagicMock
import jwt
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SECRET = "test-secret-key"
INTERNAL_TOKEN = "test-internal-token"


def _load_service_create_app(service_folder):
    service_path = os.path.join(ROOT_DIR, service_folder)
    for mod_name in list(sys.modules.keys()):
        if mod_name == "app" or mod_name.startswith("app."):
            del sys.modules[mod_name]
    sys.path.insert(0, service_path)
    try:
        spec = importlib.util.spec_from_file_location("app", os.path.join(service_path, "app", "__init__.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules["app"] = module
        spec.loader.exec_module(module)
        return module.create_app
    finally:
        sys.path.pop(0)


def make_token(user_id, role):
    now = int(time.time())
    return jwt.encode({"sub": user_id, "role": role, "iat": now, "exp": now + 3600}, SECRET, algorithm="HS256")


@pytest.fixture
def events_client(tmp_path):
    create_app = _load_service_create_app("events_service")
    db_file = tmp_path / "events_test.db"
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
        "JWT_SECRET_KEY": SECRET,
        "INTERNAL_SERVICE_TOKEN": INTERNAL_TOKEN,
    })
    with app.test_client() as client:
        yield client


@pytest.fixture
def registrations_client(tmp_path):
    create_app = _load_service_create_app("registrations_service")
    db_file = tmp_path / "registrations_test.db"
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_file}",
        "JWT_SECRET_KEY": SECRET,
        "INTERNAL_SERVICE_TOKEN": INTERNAL_TOKEN,
    })
    with app.test_client() as client:
        yield client


@pytest.fixture
def orchestrator_client():
    create_app = _load_service_create_app("orchestrator_service")
    app = create_app({
        "TESTING": True,
        "JWT_SECRET_KEY": SECRET,
        "INTERNAL_SERVICE_TOKEN": INTERNAL_TOKEN,
    })
    with app.test_client() as client:
        yield client


def test_events_lifecycle_and_rbac(events_client):
    org_token = make_token("org-1", "ORGANIZER")
    part_token = make_token("part-1", "PARTICIPANT")
    admin_token = make_token("admin-1", "ADMIN")

    # Capacidade zero deve falhar (400)
    bad_resp = events_client.post(
        "/events",
        headers={"Authorization": f"Bearer {org_token}"},
        json={
            "title": "Workshop Python",
            "description": "Prática",
            "event_type": "WORKSHOP",
            "location": "Lab 2",
            "start_at": "2026-12-01T10:00:00Z",
            "end_at": "2026-12-01T12:00:00Z",
            "capacity": 0,
        },
    )
    assert bad_resp.status_code == 400

    # Criação válida (201)
    create_resp = events_client.post(
        "/events",
        headers={"Authorization": f"Bearer {org_token}"},
        json={
            "title": "Semana de SI",
            "description": "Evento anual",
            "event_type": "ACADEMIC_WEEK",
            "location": "Auditório",
            "start_at": "2026-12-01T10:00:00Z",
            "end_at": "2026-12-02T18:00:00Z",
            "capacity": 50,
        },
    )
    assert create_resp.status_code == 201
    event_id = create_resp.get_json()["event_id"]

    # Evento PENDING não aparece na listagem pública
    assert events_client.get("/events").get_json() == []

    # PARTICIPANT não pode aprovar (403)
    forbid_resp = events_client.patch(
        f"/events/{event_id}/approve",
        headers={"Authorization": f"Bearer {part_token}"},
    )
    assert forbid_resp.status_code == 403

    # ADMIN aprova (200) e evento passa a aparecer publicamente
    approve_resp = events_client.patch(
        f"/events/{event_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_resp.status_code == 200
    assert len(events_client.get("/events").get_json()) == 1


def test_registrations_rules_and_attendance(registrations_client):
    part1_token = make_token("part-1", "PARTICIPANT")
    part2_token = make_token("part-2", "PARTICIPANT")
    admin_token = make_token("admin-1", "ADMIN")

    # Cria inscrição interna (capacidade = 1)
    r1 = registrations_client.post(
        "/internal/registrations",
        headers={"X-Internal-Token": INTERNAL_TOKEN},
        json={"event_id": "evt-1", "participant_id": "part-1", "capacity": 1},
    )
    assert r1.status_code == 201
    reg_id = r1.get_json()["registration_id"]

    # Duplicidade bloqueada (409)
    dup = registrations_client.post(
        "/internal/registrations",
        headers={"X-Internal-Token": INTERNAL_TOKEN},
        json={"event_id": "evt-1", "participant_id": "part-1", "capacity": 1},
    )
    assert dup.status_code == 409

    # Lotação máxima bloqueada (409)
    full = registrations_client.post(
        "/internal/registrations",
        headers={"X-Internal-Token": INTERNAL_TOKEN},
        json={"event_id": "evt-1", "participant_id": "part-2", "capacity": 1},
    )
    assert full.status_code == 409

    # Presença marcada pelo ADMIN
    att = registrations_client.patch(
        f"/registrations/{reg_id}/attendance",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"attendance_status": "PRESENT"},
    )
    assert att.status_code == 200

    # Consulta interna de presença para certificados
    check = registrations_client.get(
        "/internal/registrations/check-attendance?event_id=evt-1&participant_id=part-1",
        headers={"X-Internal-Token": INTERNAL_TOKEN},
    )
    assert check.status_code == 200
    assert check.get_json()["eligible"] is True

    # Cancelamento pelo próprio participante
    cancel = registrations_client.delete(
        f"/registrations/{reg_id}",
        headers={"Authorization": f"Bearer {part1_token}"},
    )
    assert cancel.status_code == 200
    assert cancel.get_json()["status"] == "CANCELLED"


@patch("requests.post")
@patch("requests.get")
def test_orchestrator_flow_and_notification_fallback(mock_get, mock_post, orchestrator_client):
    part_token = make_token("part-1", "PARTICIPANT")

    # Simula resposta do MS Events (APPROVED)
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"event_id": "evt-10", "title": "Minicurso Docker", "status": "APPROVED", "capacity": 30},
    )

    # Simula MS Registrations (201) e Notification Service fora do ar (ConnectionError)
    import requests as req_lib
    mock_post.side_effect = [
        MagicMock(
            status_code=201,
            json=lambda: {"registration_id": "reg-99", "event_id": "evt-10", "participant_id": "part-1", "status": "CONFIRMED"},
        ),
        req_lib.ConnectionError("Notification service down"),
    ]

    resp = orchestrator_client.post(
        "/registrations",
        headers={"Authorization": f"Bearer {part_token}"},
        json={"event_id": "evt-10"},
    )
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["registration_id"] == "reg-99"
    assert body["notification_status"] == "FAILED"
