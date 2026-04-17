import asyncio
import logging
import uuid
from datetime import date, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.config import settings
from src.models.fields import Field
from src.repositories.uow.base import UnitOfWork  # noqa: TCH001
from src.repositories.uow.sqlalchemy_uow import SQLAlchemyUnitOfWork
from src.schemas.meteo_data import (
    MeteoDataCreateSchema,
    MeteoDataParseSchema,
    MeteoDataTimelinePointSchema,
    SunriseSunsetPointSchema,
)
from src.scrapers.fields import FieldScraper
from src.scrapers.open_meteo import OpenMeteoScraper
from src.scrapers.sunrise_sunset import SunriseSunsetScraper

logger = logging.getLogger(__name__)


class ETLHandler:
    def __init__(self):
        self.__scheduler = AsyncIOScheduler(timezone=settings.TZ)
        self.__uow: UnitOfWork = SQLAlchemyUnitOfWork()

    def get_scheduler(self) -> AsyncIOScheduler:
        self.__scheduler.add_job(
            func=self.meteo_data_etl_job,
            trigger="cron",
            hour="*/3",
            minute=0,
            id="meteo-data-etl-job",
            replace_existing=True,
        )
        return self.__scheduler

    async def __fields_etl_job(self) -> None:
        logger.info("Fields etl job started.")
        async with FieldScraper() as scraper:
            fields = await scraper.get_all_fields()  # parse fields
        async with self.__uow:
            for field in fields:
                await self.__uow.fields.upsert(  # upsert fields data
                    data_on_insert=field.model_dump(),
                    data_on_update={
                        "longitude": field.longitude,
                        "latitude": field.latitude,
                        "parse_meteo": field.parse_meteo,
                    },
                    index_elements=["id"],
                )
            await self.__uow.commit()
        logger.info("Fields etl job completed.")

    @staticmethod
    def __normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(settings.TZ).replace(tzinfo=None)

    @staticmethod
    def __prepare_meteo_data(
        field_id: uuid.UUID, meteo_data: MeteoDataTimelinePointSchema
    ) -> MeteoDataCreateSchema:
        return MeteoDataCreateSchema(
            field_id=field_id,
            date_time=ETLHandler.__normalize_datetime(meteo_data.date_time),
            temperature=meteo_data.temperature,
            humidity=meteo_data.humidity,
            wind_speed=meteo_data.wind_speed,
            precipitation=meteo_data.precipitation,
            dew_point=meteo_data.dew_point,
            soil_temperature_0cm=meteo_data.soil_temperature_0cm,
            soil_temperature_6cm=meteo_data.soil_temperature_6cm,
            soil_temperature_18cm=meteo_data.soil_temperature_18cm,
            soil_moisture_0_to_1cm=meteo_data.soil_moisture_0_to_1cm,
            soil_moisture_1_to_3cm=meteo_data.soil_moisture_1_to_3cm,
            soil_moisture_3_to_9cm=meteo_data.soil_moisture_3_to_9cm,
            soil_moisture_9_to_27cm=meteo_data.soil_moisture_9_to_27cm,
            temperature_max=meteo_data.temperature_max,
            temperature_min=meteo_data.temperature_min,
            sunrise=ETLHandler.__normalize_datetime(meteo_data.sunrise),
            sunset=ETLHandler.__normalize_datetime(meteo_data.sunset),
            precipitation_sum=meteo_data.precipitation_sum,
        )

    async def __parse_meteo_data(
        self, fields: list[Field]
    ) -> list[MeteoDataParseSchema]:
        async with OpenMeteoScraper() as scraper:
            tasks = [
                scraper.get_meteo_data(
                    lat=field.latitude,
                    lon=field.longitude,
                    past_days=15,
                    forecast_days=16,
                )
                for field in fields
            ]
            meteo_data = await asyncio.gather(*tasks)
            return meteo_data

    async def __parse_sun_data(
        self,
        field: Field,
        days: list[date],
    ) -> dict[date, SunriseSunsetPointSchema]:
        async with SunriseSunsetScraper() as scraper:
            tasks = [
                scraper.get_sunrise_sunset_data(
                    lat=field.latitude,
                    lon=field.longitude,
                    day=day,
                    timezone=settings.TZ.tzname(None) or "Europe/Moscow",
                )
                for day in days
            ]
            results = await asyncio.gather(*tasks)
        parsed = {}
        for item in results:
            if not item:
                continue
            parsed[item.day] = item
        return parsed

    async def __save_field_meteo_data(
        self,
        field: Field,
        meteo_data: MeteoDataParseSchema,
    ) -> None:
        timeline_days = [point.date_time.date() for point in meteo_data.timeline]
        sunrise_sunset_by_day = await self.__parse_sun_data(field, timeline_days)

        all_points = [meteo_data.current, *meteo_data.timeline]
        for point in all_points:
            sun_info = sunrise_sunset_by_day.get(point.date_time.date())
            point_with_sun = point.model_copy(
                update={
                    "sunrise": sun_info.sunrise if sun_info else point.sunrise,
                    "sunset": sun_info.sunset if sun_info else point.sunset,
                }
            )
            prepared_meteo_data = self.__prepare_meteo_data(field.id, point_with_sun)
            await self.__uow.meteo_data.upsert(
                data_on_insert=prepared_meteo_data.model_dump(),
                data_on_update=prepared_meteo_data.model_dump(
                    exclude={"field_id", "date_time"}
                ),
                index_elements=["field_id", "date_time"],
            )
        await self.__uow.commit()

    async def meteo_data_etl_job(self) -> None:
        logger.info("Meteo data etl job started.")
        async with self.__uow:
            await self.__fields_etl_job()  # upsert fields data
            fields = await self.__uow.fields.read_many(parse_meteo=True)
            parsed_meteo_data = await self.__parse_meteo_data(fields)
            for field, meteo_data in zip(fields, parsed_meteo_data):
                if not meteo_data:
                    continue
                await self.__save_field_meteo_data(field, meteo_data)
            logger.info("Meteo data etl job completed.")

    async def meteo_data_etl_for_field(self, field_id: uuid.UUID) -> None:
        logger.info("Manual meteo data refresh for field %s started.", field_id)
        async with self.__uow:
            await self.__fields_etl_job()
            field = await self.__uow.fields.read(id=field_id)
            if not field or not field.parse_meteo:
                logger.info("Field %s not found or parse_meteo disabled.", field_id)
                return
            parsed_data = await self.__parse_meteo_data([field])
            meteo_data = parsed_data[0] if parsed_data else None
            if not meteo_data:
                logger.info("No meteo data parsed for field %s.", field_id)
                return
            await self.__save_field_meteo_data(field, meteo_data)
        logger.info("Manual meteo data refresh for field %s completed.", field_id)


etl_handler = ETLHandler()
