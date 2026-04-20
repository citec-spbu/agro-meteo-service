import uuid

from src.schemas.contours import ContourSchema
from src.scrapers.base import AbstractScraper
from src.scrapers.constants import ScraperConstantsEnum


class ContourScraper(AbstractScraper):
    BASE_URL_TEMPLATE = ScraperConstantsEnum.FIELDS_SERVICE_CONTOURS_URL_TEMPLATE.value

    @property
    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    async def get_field_contours(self, field_id: uuid.UUID) -> list[ContourSchema]:
        response_json = await self._get(
            ContourScraper.BASE_URL_TEMPLATE.format(field_id=field_id)
        )
        if not isinstance(response_json, list):
            return []
        return [ContourSchema.model_validate(contour) for contour in response_json]
