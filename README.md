# helsinki-rental-parser

Async rental listings parser for the Helsinki metropolitan area. Scrapes rental announcements from multiple sources, stores them in PostgreSQL, and exposes a REST API with filters and Excel export.

## Features

- Async scraping of Vuokraovi and SATO with full pagination
- Automatic detection of water/electricity included in rent (regex + structured API fields)
- Bulk upsert with deduplication — safe to re-run at any time
- Marks listings as inactive when they disappear from source
- REST API with flexible filters (price, area, district, room count, lessor type, etc.)
- Excel export with formatted output and clickable links

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Backend | FastAPI + uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Validation | Pydantic v2 + pydantic-settings |
| HTTP client | httpx (async) |
| Export | pandas + openpyxl |
| Infrastructure | Docker Compose |
| Bot (planned) | aiogram 3.x |

## Project Structure

```
helsinki-rental-parser/
├── app/
│   ├── database/
│   │   ├── base.py
│   │   ├── schemas/
│   │   │   ├── listing.py
│   │   │   ├── filter.py
│   │   │   └── seen.py
│   │   ├── db_helper.py
│   │   └── models.py
│   ├── parsers/
│   │   ├── vuokraovi.py
│   │   └── sato.py
│   ├── routers/
│   │   └── listings.py
│   ├── services/
│   │   ├── listing_service.py
│   │   └── excel_service.py
│   └── app_main.py
├── bot/
│    ├── bot_main.py          — точка входа, Dispatcher + роутеры
│    ├── keyboards.py         — все клавиатуры (Reply + Inline)
│    ├── states.py            — FSM состояния для визарда поиска
│    └── routers/
│        ├── start.py         — /start, главное меню
│        ├── search.py        — пошаговый визард фильтров (FSM)
│        ├── listings.py      — показ результатов, пагинация, экспорт
│        └── subscription.py  — управление подпиской
├── migrations/
├── config.py
├── docker-compose.yml
├── .env
└── pyproject.toml
```

## Data Sources

### Vuokraovi (vuokraovi.com)

~6000 listings. Two-step REST API: fetch listing page → fetch details by `friendlyId`.

- Filters out SATO listings by `office.customerGroupId == 26`
- Extracts water/electricity inclusion from structured `periodicCharges` fields with regex fallback
- Extracts floor plan URL, subdistrict, and lessor info from detail response

### SATO (sato.fi)

~972 listings. Single-step fetch from `searchV2` endpoint. Covers Helsinki, Espoo, and Vantaa (three separate requests).

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/listings/parse` | Trigger Vuokraovi + SATO scraping, save to DB |
| `GET` | `/listings/` | List active listings with filters |
| `GET` | `/listings/export` | Export filtered listings as `.xlsx` |

### Filter Parameters (GET /listings/)

`price_min`, `price_max`, `area_min`, `area_max`, `district`, `room_count`, `water_included`, `is_private_lessor`, `source`, `limit`, `offset`

## Database Model

The `Listing` model stores all scraped fields. Key columns:

| Column | Type | Notes |
|---|---|---|
| `external_id` | `String(50)` | Unique ID from source |
| `source` | `String(20)` | `vuokraovi` or `sato` |
| `price` | `Float` | €/month |
| `area` | `Float` | m² |
| `district` | `String(150)` | Neighbourhood |
| `address` | `String(300)` | Street address with floor |
| `room_count` | `String(30)` | e.g. `TWO_ROOMS` |
| `room_structure` | `String(100)` | Finnish notation e.g. `2h+kk` |
| `water_included` | `Boolean` | `null` if unknown |
| `water_price` | `Float` | €/month if not included |
| `electricity_included` | `Boolean` | `null` if unknown |
| `floor_plan_url` | `String(1000)` | |
| `available_from` | `String(50)` | `IMMEDIATELY` or ISO date |
| `lessor_name` | `String(200)` | |
| `is_private_lessor` | `Boolean` | |
| `is_active` | `Boolean` | Set to `False` when listing disappears |

Unique constraint: `uq_source_external_id (source, external_id)`

## Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.12 (for local development)

### Environment

Copy `.env.example` to `.env` and fill in the values:

```env
APP_DB__URL=postgresql+asyncpg://user:password@localhost:5432/parser
APP_BOT__TOKEN=your_telegram_bot_token
APP_PARSER__REQUEST_DELAY_SECONDS=1.5
APP_VUOKRAOVI__SATO_CUSTOMER_GROUP_ID=26
```

### Run with Docker

```bash
docker compose up -d
```

### Apply Migrations

```bash
alembic upgrade head
```

### Trigger Parsing

```bash
curl -X POST http://localhost:8000/listings/parse
```

## Configuration

All settings are in `config.py` using Pydantic `BaseSettings`. Environment variable prefix: `APP_`.

| Setting | Default | Description |
|---|---|---|
| `APP_DB__URL` | — | PostgreSQL async connection string |
| `APP_PARSER__REQUEST_DELAY_SECONDS` | `1.5` | Delay between requests to avoid rate limiting |
| `APP_VUOKRAOVI__SATO_CUSTOMER_GROUP_ID` | `26` | Customer group ID used to filter SATO listings from Vuokraovi results |

## Planned

- APScheduler for periodic scraping (every 30 min)
- Telegram bot (aiogram 3.x) with subscription filters and new listing notifications
- `UserFilter` and `SeenListing` endpoints for managing user subscriptions