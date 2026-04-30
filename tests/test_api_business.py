import uuid
from datetime import date, datetime

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.main import create_app
from src.schemas.meteo_data import (
    MeteoDataDashboardSchema,
    MeteoDataPeriodSchema,
    MeteoDataPreviewSchema,
    MeteoDataReadSchema,
)
from src.service import MeteoDataService


class FakeMeteoService:
    def __init__(self) -> None:
        self.raise_period_validation_error = False
        self.calls: list[tuple] = []

    @staticmethod
    def _point(field_id: uuid.UUID, dt: datetime) -> MeteoDataReadSchema:
        return MeteoDataReadSchema(
            id=uuid.uuid4(),
            field_id=field_id,
            date_time=dt,
            temperature=20.0,
            humidity=60.0,
            wind_speed=3.0,
            precipitation=0.1,
            dew_point=12.0,
            soil_temperature_0cm=16.0,
            soil_temperature_6cm=15.0,
            soil_temperature_18cm=14.0,
            soil_moisture_0_to_1cm=0.2,
            soil_moisture_1_to_3cm=0.25,
            soil_moisture_3_to_9cm=0.3,
            soil_moisture_9_to_27cm=0.35,
            temperature_max=24.0,
            temperature_min=14.0,
            sunrise=dt.replace(hour=5, minute=30),
            sunset=dt.replace(hour=20, minute=10),
            precipitation_sum=0.1,
        )

    async def get_current_meteo_data(self, field_id: uuid.UUID) -> MeteoDataDashboardSchema:
        self.calls.append(("dashboard", field_id))
        point = self._point(field_id, datetime(2026, 4, 1, 0, 0))
        return MeteoDataDashboardSchema(current=point, timeline=[point])

    async def get_meteo_data_by_period(
        self,
        field_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> MeteoDataPeriodSchema:
        self.calls.append(("period", field_id, start_date, end_date))
        if self.raise_period_validation_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be greater than end_date.",
            )
        point = self._point(field_id, datetime.combine(start_date, datetime.min.time()))
        return MeteoDataPeriodSchema(
            field_id=field_id,
            start_date=start_date,
            end_date=end_date,
            timeline=[point],
        )

    async def get_current_meteo_data_preview(self, field_id: uuid.UUID) -> MeteoDataPreviewSchema:
        self.calls.append(("preview", field_id))
        return MeteoDataPreviewSchema(
            date_time=datetime(2026, 4, 1, 12, 0),
            temperature=21.0,
            humidity=58.0,
            wind_speed=3.2,
            sunrise=datetime(2026, 4, 1, 5, 20),
            sunset=datetime(2026, 4, 1, 20, 30),
        )

    async def get_current_meteo_data_preview_by_contour(
        self,
        field_id: uuid.UUID,
        contour_id: uuid.UUID,
    ) -> MeteoDataPreviewSchema:
        self.calls.append(("contour-preview", field_id, contour_id))
        return MeteoDataPreviewSchema(
            date_time=datetime(2026, 4, 1, 12, 0),
            temperature=19.0,
            humidity=65.0,
            wind_speed=2.5,
        )

    async def refresh_meteo_data(self, field_id: uuid.UUID) -> MeteoDataDashboardSchema:
        self.calls.append(("refresh", field_id))
        point = self._point(field_id, datetime(2026, 4, 2, 0, 0))
        return MeteoDataDashboardSchema(current=point, timeline=[point])


def test_meteo_all_endpoints_positive() -> None:
    fake_service = FakeMeteoService()
    app = create_app()
    app.dependency_overrides[MeteoDataService] = lambda: fake_service
    client = TestClient(app)

    field_id = uuid.uuid4()
    contour_id = uuid.uuid4()

    dashboard = client.get(f"/api/meteo/{field_id}")
    assert dashboard.status_code == 200
    assert dashboard.json()["current"]["field_id"] == str(field_id)

    period = client.get(
        f"/api/meteo/{field_id}/period",
        params={"start_date": "2026-04-01", "end_date": "2026-04-30"},
    )
    assert period.status_code == 200
    assert period.json()["start_date"] == "2026-04-01"
    assert period.json()["end_date"] == "2026-04-30"

    preview = client.get(f"/api/meteo/preview/{field_id}")
    assert preview.status_code == 200
    assert preview.json()["temperature"] == 21.0

    by_contour = client.get(f"/api/meteo/fields/{field_id}/contours/{contour_id}/preview")
    assert by_contour.status_code == 200
    assert by_contour.json()["humidity"] == 65.0

    refresh = client.post(f"/api/meteo/{field_id}/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["current"]["field_id"] == str(field_id)

    called = [item[0] for item in fake_service.calls]
    assert called.count("dashboard") == 1
    assert called.count("period") == 1
    assert called.count("preview") == 1
    assert called.count("contour-preview") == 1
    assert called.count("refresh") == 1


def test_period_endpoint_validation_error_from_service() -> None:
    fake_service = FakeMeteoService()
    fake_service.raise_period_validation_error = True
    app = create_app()
    app.dependency_overrides[MeteoDataService] = lambda: fake_service
    client = TestClient(app)

    field_id = uuid.uuid4()
    response = client.get(
        f"/api/meteo/{field_id}/period",
        params={"start_date": "2026-04-30", "end_date": "2026-04-01"},
    )

    assert response.status_code == 400
    assert "start_date cannot be greater than end_date" in response.json()["detail"]


def test_period_endpoint_requires_dates() -> None:
    fake_service = FakeMeteoService()
    app = create_app()
    app.dependency_overrides[MeteoDataService] = lambda: fake_service
    client = TestClient(app)

    field_id = uuid.uuid4()
    response = client.get(f"/api/meteo/{field_id}/period")

    assert response.status_code == 422


def test_preview_endpoint_rejects_invalid_uuid() -> None:
    fake_service = FakeMeteoService()
    app = create_app()
    app.dependency_overrides[MeteoDataService] = lambda: fake_service
    client = TestClient(app)

    response = client.get("/api/meteo/preview/not-a-uuid")
    assert response.status_code == 422
