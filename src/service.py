import uuid
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status

from src.config import settings
from src.etl_handler import etl_handler
from src.repositories.uow.base import UnitOfWork
from src.repositories.uow.sqlalchemy_uow import SQLAlchemyUnitOfWork
from src.schemas.contours import ContourCoordinateSchema
from src.schemas.meteo_data import (
    MeteoDataDashboardSchema,
    MeteoDataPeriodSchema,
    MeteoDataPreviewSchema,
    MeteoDataReadSchema,
)
from src.scrapers.contours import ContourScraper
from src.scrapers.open_meteo import OpenMeteoScraper


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

    @staticmethod
    def __contour_centroid(
        coordinates: list[ContourCoordinateSchema],
    ) -> tuple[float, float]:
        if not coordinates:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contour coordinates not found.",
            )

        points = coordinates
        if len(points) > 1 and (
            points[0].latitude == points[-1].latitude
            and points[0].longitude == points[-1].longitude
        ):
            points = points[:-1]
        if not points:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contour coordinates not found.",
            )

        lat = sum(point.latitude for point in points) / len(points)
        lon = sum(point.longitude for point in points) / len(points)
        return lat, lon

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

    async def get_meteo_data_by_period(
        self,
        field_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> MeteoDataPeriodSchema:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be greater than end_date.",
            )

        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        async with self.__uow:
            timeline = await self.__uow.meteo_data.read_between(
                field_id=field_id,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
            )
            return MeteoDataPeriodSchema(
                field_id=field_id,
                start_date=start_date,
                end_date=end_date,
                timeline=[
                    MeteoDataReadSchema.model_validate(item, from_attributes=True)
                    for item in timeline
                ],
            )

    async def get_current_meteo_data_preview_by_contour(
        self, field_id: uuid.UUID, contour_id: uuid.UUID
    ) -> MeteoDataPreviewSchema:
        async with ContourScraper() as contour_scraper:
            contours = await contour_scraper.get_field_contours(field_id)

        contour = next((item for item in contours if item.id == contour_id), None)
        if not contour:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contour with id {contour_id} not found in field {field_id}.",
            )

        lat, lon = self.__contour_centroid(contour.coordinates)

        async with OpenMeteoScraper() as open_meteo_scraper:
            meteo_data = await open_meteo_scraper.get_meteo_data(
                lat=lat,
                lon=lon,
                past_days=1,
                forecast_days=1,
            )

        if not meteo_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meteo data for contour with id {contour_id} not found.",
            )

        return MeteoDataPreviewSchema(
            date_time=meteo_data.current.date_time,
            temperature=meteo_data.current.temperature,
            humidity=meteo_data.current.humidity,
            wind_speed=meteo_data.current.wind_speed,
            sunrise=meteo_data.current.sunrise,
            sunset=meteo_data.current.sunset,
        )

    async def refresh_meteo_data(self, field_id: uuid.UUID) -> MeteoDataDashboardSchema:
        await etl_handler.meteo_data_etl_for_field(field_id)
        return await self.get_current_meteo_data(field_id)
