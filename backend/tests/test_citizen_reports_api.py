"""Tests for citizen report creation, validation, and locations API."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.citizen_report import CitizenReport
from app.models.location import Location
from app.models.user import User


@pytest.fixture
def client():
    """Create test client with clean overrides."""
    app.dependency_overrides.pop(get_db, None)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


class MockDBSession:
    """Mock database session to test API behavior without writing to persistent DB."""

    def __init__(self, locations=None, users=None):
        self.locations = locations or {}
        self.users = users or {}
        self.added = []
        self.committed = False

    def query(self, model):
        session = self

        class MockQuery:
            def __init__(self, model_cls):
                self.model_cls = model_cls
                self.filters = []

            def filter(self, *expressions):
                self.filters.extend(expressions)
                return self

            def order_by(self, *expressions):
                return self

            def first(self):
                if self.model_cls == Location:
                    # check if any filter matches
                    for loc_id, loc in session.locations.items():
                        return loc
                    return None
                if self.model_cls == User:
                    for uid, u in session.users.items():
                        return u
                    return None
                return None

            def all(self):
                if self.model_cls == Location:
                    return list(session.locations.values())
                if self.model_cls == User:
                    return list(session.users.values())
                return []

        return MockQuery(model)

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, CitizenReport):
            if not getattr(obj, "id", None):
                obj.id = uuid4()
            if not getattr(obj, "created_at", None):
                obj.created_at = datetime.now(timezone.utc)

    def commit(self):
        self.committed = True

    def flush(self):
        pass

    def refresh(self, obj):
        if not getattr(obj, "id", None):
            obj.id = uuid4()
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(timezone.utc)


def test_create_citizen_report_valid_with_user_id(client):
    test_user_id = uuid4()
    test_loc_id = uuid4()

    mock_user = User(
        id=test_user_id,
        name="Test Citizen",
        email="test@citizen.local",
        password_hash="pw",
        role="citizen",
        is_active=True,
    )
    mock_loc = Location(
        id=test_loc_id,
        name="Pune",
        district="Pune",
        state="Maharashtra",
        country="India",
        latitude=Decimal("18.5204"),
        longitude=Decimal("73.8567"),
    )

    mock_db = MockDBSession(
        locations={test_loc_id: mock_loc},
        users={test_user_id: mock_user},
    )
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "user_id": str(test_user_id),
        "location_id": str(test_loc_id),
        "event_type": "rainfall",
        "description": "Heavy rainfall observed with water accumulation.",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "image_url": "https://example.com/rain.jpg",
    }

    response = client.post("/api/v1/citizen-reports/", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["event_type"] == "rainfall"
    assert data["location_id"] == str(test_loc_id)
    assert data["user_id"] == str(test_user_id)
    assert data["status"] == "pending"
    assert "id" in data
    assert mock_db.committed is True


def test_create_citizen_report_defaults_user_id(client):
    test_loc_id = uuid4()
    default_user_id = uuid4()

    mock_user = User(
        id=default_user_id,
        name="Default Citizen",
        email="default@citizen.local",
        password_hash="pw",
        role="citizen",
        is_active=True,
    )
    mock_loc = Location(
        id=test_loc_id,
        name="Kolhapur",
        district="Kolhapur",
        state="Maharashtra",
        country="India",
        latitude=Decimal("16.705"),
        longitude=Decimal("74.2433"),
    )

    mock_db = MockDBSession(
        locations={test_loc_id: mock_loc},
        users={default_user_id: mock_user},
    )
    app.dependency_overrides[get_db] = lambda: mock_db

    # Notice: user_id is omitted
    payload = {
        "location_id": str(test_loc_id),
        "event_type": "thunderstorm",
        "description": "Loud thunder and strong winds recorded.",
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }

    response = client.post("/api/v1/citizen-reports/", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["event_type"] == "thunderstorm"
    assert data["user_id"] == str(default_user_id)
    assert data["status"] == "pending"


def test_create_citizen_report_missing_mandatory_fields(client):
    # Missing description and reported_at
    payload = {
        "location_id": str(uuid4()),
        "event_type": "rainfall",
    }
    response = client.post("/api/v1/citizen-reports/", json=payload)
    assert response.status_code == 422


def test_create_citizen_report_invalid_event_type(client):
    payload = {
        "location_id": str(uuid4()),
        "event_type": "alien_invasion",
        "description": "Very unusual sighting.",
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/api/v1/citizen-reports/", json=payload)
    assert response.status_code == 422
    assert "Invalid event type" in response.text


def test_create_citizen_report_description_too_short(client):
    payload = {
        "location_id": str(uuid4()),
        "event_type": "rainfall",
        "description": "Hi",
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/api/v1/citizen-reports/", json=payload)
    assert response.status_code == 422


def test_create_citizen_report_unresolved_location(client):
    mock_db = MockDBSession(locations={}, users={})
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "location_id": str(uuid4()),
        "event_type": "rainfall",
        "description": "Heavy rain at non-existent location.",
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
    response = client.post("/api/v1/citizen-reports/", json=payload)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]


def test_list_locations_endpoint(client):
    loc1 = Location(
        id=uuid4(),
        name="Pune",
        district="Pune",
        state="Maharashtra",
        country="India",
        latitude=Decimal("18.5204"),
        longitude=Decimal("73.8567"),
    )
    mock_db = MockDBSession(locations={loc1.id: loc1})
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/api/v1/locations/")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0]["name"] == "Pune"
    assert items[0]["latitude"] == 18.5204
