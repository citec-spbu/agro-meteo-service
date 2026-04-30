import pytest
from fastapi import HTTPException

from src.main import create_app
from src.schemas.contours import ContourCoordinateSchema
from src.service import MeteoDataService


def test_meteo_routes_are_registered() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/meteo/{field_id}" in paths
    assert "/api/meteo/{field_id}/period" in paths
    assert "/api/meteo/preview/{field_id}" in paths
    assert "/api/meteo/fields/{field_id}/contours/{contour_id}/preview" in paths


def test_contour_centroid_ignores_closing_point() -> None:
    coords = [
        ContourCoordinateSchema(latitude=55.0, longitude=37.0),
        ContourCoordinateSchema(latitude=55.2, longitude=37.0),
        ContourCoordinateSchema(latitude=55.2, longitude=37.2),
        ContourCoordinateSchema(latitude=55.0, longitude=37.2),
        ContourCoordinateSchema(latitude=55.0, longitude=37.0),
    ]

    lat, lon = MeteoDataService._MeteoDataService__contour_centroid(coords)

    assert lat == pytest.approx(55.1)
    assert lon == pytest.approx(37.1)


def test_contour_centroid_raises_for_empty_coordinates() -> None:
    with pytest.raises(HTTPException) as exc:
        MeteoDataService._MeteoDataService__contour_centroid([])

    assert exc.value.status_code == 404
