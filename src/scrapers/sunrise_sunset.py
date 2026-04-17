from datetime import date

from src.schemas.meteo_data import SunriseSunsetPointSchema
from src.scrapers.base import AbstractScraper
from src.scrapers.constants import ScraperConstantsEnum


class SunriseSunsetScraper(AbstractScraper):
    BASE_URL = ScraperConstantsEnum.SUNRISE_SUNSET_URL.value

    @property
    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    async def get_sunrise_sunset_data(
        self,
        lat: float,
        lon: float,
        day: date,
        timezone: str,
    ) -> SunriseSunsetPointSchema | None:
        response_json = await self._get(
            SunriseSunsetScraper.BASE_URL,
            params={
                "lat": lat,
                "lng": lon,
                "date": day.isoformat(),
                "formatted": 0,
                "tzid": timezone,
            },
        )
        if not response_json or response_json.get("status") != "OK":
            return None
        results = response_json.get("results", {})
        sunrise_raw = results.get("sunrise")
        sunset_raw = results.get("sunset")
        return SunriseSunsetPointSchema(
            day=day,
            sunrise=sunrise_raw,
            sunset=sunset_raw,
        )
