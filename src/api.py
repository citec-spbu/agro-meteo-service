import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.schemas.meteo_data import (
    MeteoDataDashboardSchema,
    MeteoDataPeriodSchema,
    MeteoDataPreviewSchema,
)
from src.service import MeteoDataService

router = APIRouter(prefix="/api/meteo", tags=["meteo data"])


@router.get("/{field_id}", response_model=MeteoDataDashboardSchema)
async def get_current_meteo_data(
    field_id: uuid.UUID, service: Annotated[MeteoDataService, Depends()]
):
    return await service.get_current_meteo_data(field_id)


@router.get("/{field_id}/period", response_model=MeteoDataPeriodSchema)
async def get_meteo_data_by_period(
    field_id: uuid.UUID,
    service: Annotated[MeteoDataService, Depends()],
    start_date: Annotated[date, Query(description="Start date, inclusive")],
    end_date: Annotated[date, Query(description="End date, inclusive")],
):
    return await service.get_meteo_data_by_period(
        field_id=field_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/preview/{field_id}", response_model=MeteoDataPreviewSchema)
async def get_current_meteo_data_preview(
    field_id: uuid.UUID, service: Annotated[MeteoDataService, Depends()]
):
    return await service.get_current_meteo_data_preview(field_id)


@router.get(
    "/fields/{field_id}/contours/{contour_id}/preview",
    response_model=MeteoDataPreviewSchema,
)
async def get_current_meteo_data_preview_by_contour(
    service: Annotated[MeteoDataService, Depends()],
    field_id: uuid.UUID,
    contour_id: uuid.UUID,
):
    return await service.get_current_meteo_data_preview_by_contour(field_id, contour_id)


@router.post("/{field_id}/refresh", response_model=MeteoDataDashboardSchema)
async def refresh_meteo_data(
    field_id: uuid.UUID, service: Annotated[MeteoDataService, Depends()]
):
    return await service.refresh_meteo_data(field_id)
