import uuid

import pytest
from fastapi.testclient import TestClient

from src.main import create_app
from src.service import MeteoDataService
from tests.test_api_business import FakeMeteoService


@pytest.mark.parametrize(
    ("method", "path_template", "query", "expected_status"),
    [
        ("get", "/api/meteo/not-a-uuid", {}, 422),
        ("get", "/api/meteo/{field_id}/period", {}, 422),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "2026-04-01"}, 422),
        ("get", "/api/meteo/{field_id}/period", {"end_date": "2026-04-30"}, 422),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "bad", "end_date": "2026-04-30"}, 422),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "2026-04-01", "end_date": "bad"}, 422),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "2026-04-01", "end_date": "2026-04-30"}, 200),
        ("get", "/api/meteo/preview/not-a-uuid", {}, 422),
        ("get", "/api/meteo/preview/{field_id}", {}, 200),
        ("get", "/api/meteo/fields/{field_id}/contours/not-a-uuid/preview", {}, 422),
        ("get", "/api/meteo/fields/not-a-uuid/contours/{contour_id}/preview", {}, 422),
        ("get", "/api/meteo/fields/{field_id}/contours/{contour_id}/preview", {}, 200),
        ("post", "/api/meteo/not-a-uuid/refresh", {}, 422),
        ("post", "/api/meteo/{field_id}/refresh", {}, 200),
        ("get", "/api/meteo/{field_id}", {}, 200),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "2026-02-29", "end_date": "2026-04-30"}, 422),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "2026-04-30", "end_date": "2026-04-01"}, 200),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "2026-04-01", "end_date": "2026-04-01"}, 200),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "2026-01-01", "end_date": "2027-01-01"}, 200),
        ("get", "/api/meteo/{field_id}/period", {"start_date": "2026-4-1", "end_date": "2026-4-30"}, 422),
    ],
)
def test_meteo_validation_matrix(
    method: str,
    path_template: str,
    query: dict[str, str],
    expected_status: int,
) -> None:
    fake_service = FakeMeteoService()
    app = create_app()
    app.dependency_overrides[MeteoDataService] = lambda: fake_service
    client = TestClient(app)

    path = path_template.format(field_id=uuid.uuid4(), contour_id=uuid.uuid4())
    response = client.request(method.upper(), path, params=query)
    assert response.status_code == expected_status
