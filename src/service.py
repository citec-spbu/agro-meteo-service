import uuid
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.config import settings
from src.etl_handler import etl_handler
from src.repositories.uow.base import UnitOfWork
from src.repositories.uow.sqlalchemy_uow import SQLAlchemyUnitOfWork
from src.schemas.meteo_data import (
    MeteoDataDashboardSchema,
    MeteoDataPreviewSchema,
    MeteoDataReadSchema,
)


class MeteoDataService:
    def __init__(self, uow: Annotated[UnitOfWork, Depends(SQLAlchemyUnitOfWork)]):
        self.__uow = uow

    @staticmethod
    def __deduplicate_timeline_by_day(timeline: list) -> list:
        grouped = {}
        for item in timeline:
            day = item.date_time.date()
            if day not in grouped:
                grouped[day] = item
                continue
            existing = grouped[day]
            item_is_daily = item.date_time.hour == 0 and item.date_time.minute == 0
            existing_is_daily = (
                existing.date_time.hour == 0 and existing.date_time.minute == 0
            )
            if item_is_daily and not existing_is_daily:
                grouped[day] = item
                continue
            if item_is_daily == existing_is_daily and item.date_time > existing.date_time:
                grouped[day] = item
        return [grouped[d] for d in sorted(grouped.keys())]

    async def get_current_meteo_data(self, field_id: uuid.UUID) -> MeteoDataDashboardSchema:
        start_date = datetime.combine(date.today() - timedelta(days=15), datetime.min.time())
        end_date = datetime.combine(date.today() + timedelta(days=15), datetime.max.time())
        async with self.__uow:
            now_local_naive = datetime.now(settings.TZ).replace(tzinfo=None)
            current = await self.__uow.meteo_data.read_last_before(
                field_id=field_id,
                before_datetime=now_local_naive,
            )
            if not current:
                current = await self.__uow.meteo_data.read_last_by_datetime(field_id=field_id)
            if not current:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Meteo data for field with id {field_id} not found.",
                )
            raw_timeline = await self.__uow.meteo_data.read_between(
                field_id=field_id,
                start_datetime=start_date,
                end_datetime=end_date,
            )
            timeline = self.__deduplicate_timeline_by_day(raw_timeline)
            return MeteoDataDashboardSchema(
                current=MeteoDataReadSchema.model_validate(current, from_attributes=True),
                timeline=[
                    MeteoDataReadSchema.model_validate(item, from_attributes=True)
                    for item in timeline
                ],
            )

    async def get_current_meteo_data_preview(
        self, field_id: uuid.UUID
    ) -> MeteoDataPreviewSchema:
        async with self.__uow:
            res = await self.__uow.meteo_data.read_last_by_datetime(field_id=field_id)
            if not res:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Meteo data for field with id {field_id} not found.",
                )
            return MeteoDataPreviewSchema.model_validate(res, from_attributes=True)

    async def refresh_meteo_data(self, field_id: uuid.UUID) -> MeteoDataDashboardSchema:
        await etl_handler.meteo_data_etl_for_field(field_id)
        return await self.get_current_meteo_data(field_id)
