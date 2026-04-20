import uuid

from pydantic import BaseModel, Field


class ContourCoordinateSchema(BaseModel):
    longitude: float
    latitude: float


class ContourSchema(BaseModel):
    id: uuid.UUID
    name: str | None = None
    coordinates: list[ContourCoordinateSchema] = Field(default_factory=list)
