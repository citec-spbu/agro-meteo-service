from enum import Enum


class ScraperConstantsEnum(Enum):
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
    SUNRISE_SUNSET_URL = "https://api.sunrise-sunset.org/json"
    FIELDS_SERVICE_URL = "http://fields-service:8080/api/internal/fields-service/fields/all-coordinates"
    TIMEOUT = 60
    RETRY_ATTEMPTS = 3
    WAIT_BETWEEN_RETRIES_SEC = 5
