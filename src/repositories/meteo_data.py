import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.meteo_data import MeteoData
from src.repositories.sqlalchemy_repository import SQLAlchemyRepository


class MeteoDataRepository(SQLAlchemyRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MeteoData, session)

    async def read_last_by_datetime(self, field_id: uuid.UUID) -> MeteoData | None:
        res = await self.session.execute(
            select(MeteoData)
            .filter_by(field_id=field_id)
            .order_by(MeteoData.date_time.desc())
            .limit(1)
        )
        return res.scalars().first()

    async def read_between(
        self,
        field_id: uuid.UUID,
        start_datetime: datetime,
        end_datetime: datetime,
    ) -> list[MeteoData]:
        res = await self.session.execute(
            select(MeteoData)
            .filter(MeteoData.field_id == field_id)
            .filter(MeteoData.date_time >= start_datetime)
            .filter(MeteoData.date_time <= end_datetime)
            .order_by(MeteoData.date_time.asc())
        )
        return res.scalars().all()

    async def read_last_before(
        self,
        field_id: uuid.UUID,
        before_datetime: datetime,
    ) -> MeteoData | None:
        res = await self.session.execute(
            select(MeteoData)
            .filter(MeteoData.field_id == field_id)
            .filter(MeteoData.date_time <= before_datetime)
            .order_by(MeteoData.date_time.desc())
            .limit(1)
        )
        return res.scalars().first()
