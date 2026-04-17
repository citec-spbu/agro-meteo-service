import uuid
from datetime import date, datetime

from pydantic import BaseModel


class MeteoDataTimelinePointSchema(BaseModel):
    date_time: datetime
    temperature: float | None
    humidity: float | None
    wind_speed: float | None
    precipitation: float | None
    dew_point: float | None
    soil_temperature_0cm: float | None
    soil_temperature_6cm: float | None
    soil_temperature_18cm: float | None
    soil_moisture_0_to_1cm: float | None
    soil_moisture_1_to_3cm: float | None
    soil_moisture_3_to_9cm: float | None
    soil_moisture_9_to_27cm: float | None
    temperature_max: float | None
    temperature_min: float | None
    sunrise: datetime | None
    sunset: datetime | None
    precipitation_sum: float | None


class MeteoDataParseSchema(BaseModel):
    current: MeteoDataTimelinePointSchema
    timeline: list[MeteoDataTimelinePointSchema]


class SunriseSunsetPointSchema(BaseModel):
    day: date
    sunrise: datetime | None
    sunset: datetime | None


class MeteoDataCreateSchema(BaseModel):
    field_id: uuid.UUID
    date_time: datetime

    temperature: float | None
    humidity: float | None
    wind_speed: float | None
    precipitation: float | None
    dew_point: float | None
    soil_temperature_0cm: float | None
    soil_temperature_6cm: float | None
    soil_temperature_18cm: float | None
    soil_moisture_0_to_1cm: float | None
    soil_moisture_1_to_3cm: float | None
    soil_moisture_3_to_9cm: float | None
    soil_moisture_9_to_27cm: float | None

    temperature_max: float | None
    temperature_min: float | None
    sunrise: datetime | None
    sunset: datetime | None
    precipitation_sum: float | None


class MeteoDataReadSchema(MeteoDataCreateSchema):
    id: uuid.UUID


class MeteoDataDashboardSchema(BaseModel):
    current: MeteoDataReadSchema
    timeline: list[MeteoDataReadSchema]


class MeteoDataPreviewSchema(BaseModel):
    date_time: datetime
    temperature: float | None
    humidity: float | None
    wind_speed: float | None
    sunrise: datetime | None = None
    sunset: datetime | None = None
