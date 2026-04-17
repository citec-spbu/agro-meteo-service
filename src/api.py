import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from src.schemas.meteo_data import MeteoDataDashboardSchema, MeteoDataPreviewSchema
from src.service import MeteoDataService

router = APIRouter(prefix="/api/meteo", tags=["meteo data"])


@router.get("/{field_id}", response_model=MeteoDataDashboardSchema)
async def get_current_meteo_data(
    field_id: uuid.UUID, service: Annotated[MeteoDataService, Depends()]
):
    return await service.get_current_meteo_data(field_id)


@router.get("/preview/{field_id}", response_model=MeteoDataPreviewSchema)
async def get_current_meteo_data_preview(
    field_id: uuid.UUID, service: Annotated[MeteoDataService, Depends()]
):
    return await service.get_current_meteo_data_preview(field_id)


@router.post("/{field_id}/refresh", response_model=MeteoDataDashboardSchema)
async def refresh_meteo_data(
    field_id: uuid.UUID, service: Annotated[MeteoDataService, Depends()]
):
    return await service.refresh_meteo_data(field_id)
