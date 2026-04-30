# agro-meteo-service

Микросервис метеоданных: хранение и выдача наблюдений/прогнозов для полей.

## Стек
- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy v2
- APScheduler

## Быстрый запуск
```bash
docker network create agronetwork 2>/dev/null || true
docker compose up -d --build
```

Сервис доступен на `http://localhost:8003`, Swagger - `http://localhost:8003/docs`.
База данных доступна на `localhost:5436`.

## Миграции
```bash
docker compose run --rm migrations
```

## Переменные окружения
Конфигурация хранится в `.env` и подключается через `docker-compose.yml`.