"""Tests for the temperature prediction and forecast endpoints."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.temperature_forecast import TemperatureForecast


@pytest.fixture
def client():
    """Create an API client and clean up the dependency override."""
    app.dependency_overrides.pop(get_db, None)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_db, None)


def make_forecast(
    location="Pune",
    model_name="random_forest",
    temperature=Decimal("30.50"),
):
    """Create a forecast-like object without writing to the database."""
    return SimpleNamespace(
        id=uuid4(),
        observation_id=uuid4(),
        model_name=model_name,
        location=location,
        forecast_horizon_hours=3,
        predicted_temperature_c=temperature,
        created_at=datetime(
            2026, 10, 15, 10, 0, tzinfo=timezone.utc
        ),
    )


class FakeQuery:
    """Provide the query methods used by the forecast endpoints."""

    def __init__(
        self,
        rows=None,
        summary=None,
        model_counts=None,
        calls=None,
        query_type="forecasts",
    ):
        self.rows = rows if rows is not None else []
        self.summary = summary
        self.model_counts = (
            model_counts if model_counts is not None else []
        )
        self.calls = calls if calls is not None else {}
        self.query_type = query_type

    def filter(self, expression):
        self.calls["filter"] = expression
        return self

    def order_by(self, expression):
        self.calls.setdefault("order_by", []).append(expression)
        return self

    def offset(self, value):
        self.calls["offset"] = value
        return self

    def limit(self, value):
        self.calls["limit"] = value
        return self

    def group_by(self, expression):
        self.calls["group_by"] = expression
        return self

    def all(self):
        if self.query_type == "model_counts":
            return self.model_counts
        return self.rows

    def one(self):
        return self.summary


class FakeSession:
    """Return predefined results instead of querying PostgreSQL."""

    def __init__(self, forecasts=None, summary=None, model_counts=None):
        self.forecasts = forecasts if forecasts is not None else []
        self.summary = summary
        self.model_counts = (
            model_counts if model_counts is not None else []
        )
        self.calls = {"query_types": []}

    def query(self, *entities):
        self.calls["query_types"].append(len(entities))

        if len(entities) == 1 and entities[0] is TemperatureForecast:
            return FakeQuery(
                rows=self.forecasts,
                calls=self.calls,
                query_type="forecasts",
            )

        if len(entities) == 2:
            return FakeQuery(
                model_counts=self.model_counts,
                calls=self.calls,
                query_type="model_counts",
            )

        return FakeQuery(
            summary=self.summary,
            calls=self.calls,
            query_type="summary",
        )


def override_database(fake_session):
    """Replace the real database dependency for a test."""

    def get_fake_db():
        yield fake_session

    app.dependency_overrides[get_db] = get_fake_db


def test_list_forecasts_returns_forecasts(client):
    forecast = make_forecast()
    fake_db = FakeSession(forecasts=[forecast])
    override_database(fake_db)

    response = client.get(
        "/api/v1/temperature-predictions/forecasts"
    )

    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(forecast.id)
    assert data[0]["location"] == "Pune"
    assert data[0]["model_name"] == "random_forest"
    assert float(data[0]["predicted_temperature_c"]) == 30.50


def test_list_forecasts_applies_location_and_pagination(client):
    fake_db = FakeSession()
    override_database(fake_db)

    response = client.get(
        "/api/v1/temperature-predictions/forecasts"
        "?location=Pune&page=2&page_size=5"
    )

    assert response.status_code == 200
    assert response.json() == []
    assert "filter" in fake_db.calls
    assert fake_db.calls["offset"] == 5
    assert fake_db.calls["limit"] == 5


@pytest.mark.parametrize(
    "query",
    [
        "?page=0",
        "?page_size=0",
        "?page_size=101",
    ],
)
def test_list_forecasts_rejects_invalid_pagination(client, query):
    override_database(FakeSession())

    response = client.get(
        "/api/v1/temperature-predictions/forecasts" + query
    )

    assert response.status_code == 422


def test_summary_returns_aggregate_statistics(client):
    latest = datetime(
        2026, 10, 15, 10, 0, tzinfo=timezone.utc
    )

    fake_db = FakeSession(
        summary=SimpleNamespace(
            total_forecasts=3,
            average_predicted_temperature_c=Decimal("28.50"),
            minimum_predicted_temperature_c=Decimal("22.00"),
            maximum_predicted_temperature_c=Decimal("35.00"),
            latest_forecast_at=latest,
        ),
        model_counts=[
            SimpleNamespace(
                model_name="random_forest", count=2
            ),
            SimpleNamespace(
                model_name="xgboost", count=1
            ),
        ],
    )
    override_database(fake_db)

    response = client.get(
        "/api/v1/temperature-predictions/summary"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total_forecasts"] == 3
    assert data["average_predicted_temperature_c"] == 28.5
    assert data["minimum_predicted_temperature_c"] == 22.0
    assert data["maximum_predicted_temperature_c"] == 35.0
    assert data["latest_forecast_at"] is not None
    assert data["forecasts_by_model"] == [
        {"model_name": "random_forest", "count": 2},
        {"model_name": "xgboost", "count": 1},
    ]


def test_summary_handles_empty_database(client):
    fake_db = FakeSession(
        summary=SimpleNamespace(
            total_forecasts=0,
            average_predicted_temperature_c=None,
            minimum_predicted_temperature_c=None,
            maximum_predicted_temperature_c=None,
            latest_forecast_at=None,
        ),
        model_counts=[],
    )
    override_database(fake_db)

    response = client.get(
        "/api/v1/temperature-predictions/summary"
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_forecasts": 0,
        "average_predicted_temperature_c": None,
        "minimum_predicted_temperature_c": None,
        "maximum_predicted_temperature_c": None,
        "latest_forecast_at": None,
        "forecasts_by_model": [],
    }