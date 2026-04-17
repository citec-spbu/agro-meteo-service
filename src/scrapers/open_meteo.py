import logging
from datetime import datetime
from collections import defaultdict

from pydantic import ValidationError

from src.schemas.meteo_data import MeteoDataParseSchema, MeteoDataTimelinePointSchema
from src.scrapers.base import AbstractScraper
from src.scrapers.constants import ScraperConstantsEnum

logger = logging.getLogger(__name__)


class OpenMeteoScraper(AbstractScraper):
    BASE_URL: str = ScraperConstantsEnum.OPEN_METEO_URL.value

    @property
    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    async def get_meteo_data(
        self, lat: float, lon: float, past_days: int = 15, forecast_days: int = 16
    ) -> MeteoDataParseSchema | None:
        response_json = await self._get(
            OpenMeteoScraper.BASE_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,dew_point_2m,soil_temperature_0cm,soil_temperature_6cm,soil_temperature_18cm,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm",  # noqa: E501
                "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,dew_point_2m,soil_temperature_0cm,soil_temperature_6cm,soil_temperature_18cm,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm",  # noqa: E501
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "wind_speed_unit": "ms",
                "timezone": "Europe/Moscow",
                "forecast_days": forecast_days,
                "past_days": past_days,
                "timeformat": "iso8601",
            },
        )
        try:
            hourly = response_json["hourly"]
            hourly_times = [datetime.fromisoformat(v) for v in hourly["time"]]
            grouped_indices = defaultdict(list)
            for idx, ts in enumerate(hourly_times):
                grouped_indices[ts.date().isoformat()].append(idx)

            daily = response_json.get("daily", {})
            daily_time = daily.get("time", [])
            daily_t_max = daily.get("temperature_2m_max", [])
            daily_t_min = daily.get("temperature_2m_min", [])
            daily_prec_sum = daily.get("precipitation_sum", [])
            daily_map = {
                day: {
                    "temperature_max": daily_t_max[i] if i < len(daily_t_max) else None,
                    "temperature_min": daily_t_min[i] if i < len(daily_t_min) else None,
                    "precipitation_sum": daily_prec_sum[i] if i < len(daily_prec_sum) else None,
                }
                for i, day in enumerate(daily_time)
            }

            def _avg(values: list[float | None]) -> float | None:
                filtered = [v for v in values if v is not None]
                if not filtered:
                    return None
                return sum(filtered) / len(filtered)

            def _max(values: list[float | None]) -> float | None:
                filtered = [v for v in values if v is not None]
                if not filtered:
                    return None
                return max(filtered)

            def _sum(values: list[float | None]) -> float | None:
                filtered = [v for v in values if v is not None]
                if not filtered:
                    return None
                return sum(filtered)

            current = MeteoDataTimelinePointSchema(
                date_time=datetime.fromisoformat(response_json["current"]["time"]),
                temperature=response_json["current"].get("temperature_2m"),
                humidity=response_json["current"].get("relative_humidity_2m"),
                wind_speed=response_json["current"].get("wind_speed_10m"),
                precipitation=response_json["current"].get("precipitation"),
                dew_point=response_json["current"].get("dew_point_2m"),
                soil_temperature_0cm=response_json["current"].get("soil_temperature_0cm"),
                soil_temperature_6cm=response_json["current"].get("soil_temperature_6cm"),
                soil_temperature_18cm=response_json["current"].get("soil_temperature_18cm"),
                soil_moisture_0_to_1cm=response_json["current"].get("soil_moisture_0_to_1cm"),
                soil_moisture_1_to_3cm=response_json["current"].get("soil_moisture_1_to_3cm"),
                soil_moisture_3_to_9cm=response_json["current"].get("soil_moisture_3_to_9cm"),
                soil_moisture_9_to_27cm=response_json["current"].get("soil_moisture_9_to_27cm"),
                temperature_max=None,
                temperature_min=None,
                sunrise=None,
                sunset=None,
                precipitation_sum=None,
            )
            timeline = []
            for iso_day in sorted(grouped_indices.keys()):
                indices = grouped_indices[iso_day]
                day_daily = daily_map.get(iso_day, {})

                def pick(name: str) -> list[float | None]:
                    values = hourly.get(name, [])
                    return [values[i] if i < len(values) else None for i in indices]

                timeline.append(
                    MeteoDataTimelinePointSchema(
                        date_time=datetime.fromisoformat(iso_day),
                        temperature=_avg(pick("temperature_2m")),
                        humidity=_avg(pick("relative_humidity_2m")),
                        wind_speed=_max(pick("wind_speed_10m")),
                        precipitation=_sum(pick("precipitation")),
                        dew_point=_avg(pick("dew_point_2m")),
                        soil_temperature_0cm=_avg(pick("soil_temperature_0cm")),
                        soil_temperature_6cm=_avg(pick("soil_temperature_6cm")),
                        soil_temperature_18cm=_avg(pick("soil_temperature_18cm")),
                        soil_moisture_0_to_1cm=_avg(pick("soil_moisture_0_to_1cm")),
                        soil_moisture_1_to_3cm=_avg(pick("soil_moisture_1_to_3cm")),
                        soil_moisture_3_to_9cm=_avg(pick("soil_moisture_3_to_9cm")),
                        soil_moisture_9_to_27cm=_avg(pick("soil_moisture_9_to_27cm")),
                        temperature_max=day_daily.get("temperature_max"),
                        temperature_min=day_daily.get("temperature_min"),
                        sunrise=None,
                        sunset=None,
                        precipitation_sum=day_daily.get("precipitation_sum"),
                    )
                )
            meteo_data = MeteoDataParseSchema(current=current, timeline=timeline)
        except (KeyError, TypeError, ValidationError):
            logger.debug("%s - couldn't parse meteo data.", (lat, lon))
            return None
        return meteo_data
