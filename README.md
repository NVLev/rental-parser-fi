# helsinki-rental-parser

[🇷🇺 Читать на русском](#russian-version)

Async rental listings parser for the Helsinki metropolitan area. Scrapes rental announcements from multiple sources, stores them in PostgreSQL, and exposes a REST API with filters and Excel export. Includes a Telegram bot with search wizard, subscriptions, and new listing notifications.

## ✨ Features

- ⚡ Async scraping of Vuokraovi (~10 800 listings) and SATO (~930 listings) with full pagination  
- 💧 Automatic detection of water/electricity included in rent (structured API fields + regex fallback)  
- 🏘️ ARA (state-subsidised) and student housing detection  
- 🔁 Bulk upsert with deduplication — safe to re-run anytime  
- ❌ Marks listings as inactive when they disappear from source  
- 🔍 REST API with flexible filters  
- 📊 Excel export with formatted output and clickable links  
- 🤖 Telegram bot with FSM search wizard, pagination, subscriptions, notifications  
- ⏰ APScheduler for periodic scraping (every 12 hours)  
- 📝 Rotating logs for app and bot  

## 🧱 Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Backend | FastAPI + uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Validation | Pydantic v2 + pydantic-settings |
| HTTP client | httpx (async) |
| Scheduler | APScheduler 3.x (AsyncIOScheduler) |
| Export | pandas + openpyxl |
| Infrastructure | Docker Compose |
| Bot | aiogram 3.x |

## 📁 Project Structure

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
│   │   ├── excel_service.py
│   │   └── scheduler.py
│   └── app_main.py
├── bot/
│   ├── bot_main.py
│   ├── keyboards.py
│   ├── states.py
│   ├── routers/
│   │   ├── start.py
│   │   ├── search.py
│   │   ├── listings.py
│   │   └── subscription.py
│   └── services/
│       └── user_filter_service.py
├── migrations/
├── logs/
├── config.py
├── Dockerfile
├── docker-compose.yml
├── .env
└── pyproject.toml
```

## Data Sources

### Vuokraovi (vuokraovi.com)

~10 800 listings. Two-step REST API: fetch listing page → fetch details by `friendlyId`.

- Filters out SATO listings by `office.customerGroupId == 26`
- Extracts water/electricity inclusion from structured `periodicCharges` fields with regex fallback
- Extracts ARA and student home status from `residenceDetailsDTO.livingFormType`
- Extracts floor plan URL, subdistrict, and lessor info from detail response
- Parallel detail fetching via `asyncio.Semaphore(concurrency=10)` (~15 min vs ~5 hours sequential)

### SATO (sato.fi)

~930 listings. Single-step fetch from `searchV2` endpoint. Covers Helsinki, Espoo, and Vantaa (three separate requests).

- Extracts ARA and student home status from `apartment.flags.isAra` / `flags.studentHome`

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/listings/parse` | Trigger Vuokraovi + SATO scraping, save to DB |
| `GET` | `/listings/` | List active listings with filters |
| `GET` | `/listings/export` | Export filtered listings as `.xlsx` |

### Filter Parameters (GET /listings/)

`price_min`, `price_max`, `area_min`, `area_max`, `district`, `room_count`, `water_included`, `electricity_included`, `is_private_lessor`, `is_ara`, `is_student_home`, `source`, `limit`, `offset`

## Database Model

### Listing

| Column | Type | Notes |
|---|---|---|
| `external_id` | `String(50)` | Unique ID from source |
| `source` | `String(20)` | `vuokraovi` or `sato` |
| `url` | `String(500)` | Link to listing |
| `price` | `Float` | €/month |
| `area` | `Float` | m² |
| `district` | `String(200)` | Neighbourhood |
| `address` | `String(300)` | Street address with floor |
| `room_count` | `String(30)` | e.g. `TWO_ROOMS` |
| `room_structure` | `String(150)` | Finnish notation e.g. `2h+kk` |
| `water_included` | `Boolean` | `null` if unknown |
| `water_price` | `Float` | €/month if not included |
| `electricity_included` | `Boolean` | `null` if unknown |
| `floor_plan_url` | `String(1000)` | |
| `available_from` | `String(50)` | `IMMEDIATELY` or ISO date |
| `lessor_name` | `String(250)` | |
| `is_private_lessor` | `Boolean` | |
| `is_ara` | `Boolean` | `null` if unknown |
| `is_student_home` | `Boolean` | `null` if unknown |
| `published_at` | `TIMESTAMP(tz)` | |
| `is_active` | `Boolean` | Set to `False` when listing disappears |

Unique constraint: `uq_source_external_id (source, external_id)`

### UserFilter

Stores per-user subscription filters: price, area, districts, room counts, water/electricity included, lessor type, ARA, student home, source.

### SeenListing

Tracks which listings have been sent to each user to avoid duplicate notifications.

## Setup

### Prerequisites

- Docker & Docker Compose


### Environment

Copy `.env.example` to `.env` and fill in:

```env
APP_DB__URL=postgresql+asyncpg://rental_parser_user:password@pg:5432/rental_parser
APP_BOT__TOKEN=your_telegram_bot_token
APP_PARSER__REQUEST_DELAY_SECONDS=1.5
APP_PARSER__CONCURRENCY=10
APP_PARSER__CHECK_INTERVAL_MINUTES=720
APP_PARSER__NOTIFICATION_LIMIT=50
APP_VUOKRAOVI__SATO_CUSTOMER_GROUP_ID=26
```

## 🚀 Setup & Run

### 1. Clone repository

```bash
git clone https://github.com/NVLev/rental-parser-fi
cd rental-parser-fi
```

---

### 2. Prepare environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
APP_DB__URL=postgresql+asyncpg://rental_parser_user:password@pg:5432/rental_parser
APP_BOT__TOKEN=your_telegram_bot_token
APP_PARSER__REQUEST_DELAY_SECONDS=1.5
APP_PARSER__CONCURRENCY=10
APP_PARSER__CHECK_INTERVAL_MINUTES=720
APP_PARSER__NOTIFICATION_LIMIT=50
APP_VUOKRAOVI__SATO_CUSTOMER_GROUP_ID=26
```

---

### 3. Build containers

```bash
docker compose build
```

---

### 4. Run project

```bash
docker compose up -d
```

📌 On startup:
- PostgreSQL launches
- Alembic migrations are applied automatically
- FastAPI app starts on http://localhost:8002

---


### Trigger Parsing Manually

```bash
curl -X POST http://localhost:8000/listings/parse
```

### 📡 API Docs

Available at `http://localhost:8000/docs` after startup.

## Configuration

| Setting | Default | Description |
|---|---|---|
| `APP_DB__URL` | — | PostgreSQL async connection string |
| `APP_BOT__TOKEN` | — | Telegram bot token |
| `APP_PARSER__REQUEST_DELAY_SECONDS` | `1.5` | Delay between requests |
| `APP_PARSER__CONCURRENCY` | `10` | Parallel detail fetches (Vuokraovi) |
| `APP_PARSER__CHECK_INTERVAL_MINUTES` | `720` | Scheduler interval (12 hours) |
| `APP_PARSER__NOTIFICATION_LIMIT` | `50` | Max listings per notification cycle per user |
| `APP_VUOKRAOVI__SATO_CUSTOMER_GROUP_ID` | `26` | Customer group ID to filter SATO from Vuokraovi |

## 🔎 Filters

price_min, price_max, area_min, area_max, district,  
room_count, water_included, electricity_included,  
is_private_lessor, is_ara, is_student_home, source,  
limit, offset

---

## 🗄️ Database Model

### Listing

- external_id — unique per source  
- source — vuokraovi / sato  
- price, area, district, address  
- room_count, room_structure  
- utilities: water / electricity  
- lessor_name, is_private_lessor  
- is_ara, is_student_home  
- published_at, is_active  

🔒 Unique constraint: (source, external_id)

---

## 📊 Data Sources

### Vuokraovi

- ~10 800 listings  
- Two-step API (list → details)  
- Parallel detail fetching (10 workers)  

### SATO

- ~930 listings  
- Single API request (searchV2)  
- Covers Helsinki, Espoo, Vantaa  

---

## 🔌 Extending

Additional sources that follow a similar REST API pattern and could be integrated:
 
- [Lumo](https://lumo.fi) — major Finnish rental housing company
- [Oikotie Asunnot](https://asunnot.oikotie.fi) — large Finnish property marketplace


---
## 🧑‍💻 Authors and Credits

### Project Author
**Natalia Levant** 
GitHub: [https://github.com/NVLev](https://github.com/NVLev)

### Copyright Notice
© 2026 Natalia Levant 
The project is released for educational and research purposes.  
Non-commercial use is permitted with attribution.  
Commercial use requires explicit permission from the copyright holders.


## Russian Version

<a name="russian-version"></a>

# 🏠 helsinki-rental-parser

Асинхронный парсер объявлений об аренде жилья в Хельсинкском регионе. Собирает объявления из нескольких источников, сохраняет в PostgreSQL, предоставляет REST API с фильтрами и экспортом в Excel. Включает Telegram-бот с визардом поиска, подписками и уведомлениями о новых объявлениях.

## Возможности

- Асинхронный парсинг Vuokraovi (~10 800 объявлений) и SATO (~930 объявлений) с полной пагинацией
- Автоматическое определение включения воды/электричества в аренду (структурированные поля API + regex)
- Определение ARA (государственное субсидированное жильё) и студенческого жилья для обоих источников
- Массовый upsert с дедупликацией — безопасно запускать повторно в любое время
- Помечает объявления неактивными, когда они исчезают из источника
- REST API с гибкими фильтрами (цена, площадь, район, количество комнат, тип арендодателя, ARA, студенческое жильё и др.)
- Экспорт в Excel с форматированием и кликабельными ссылками
- Telegram-бот с FSM-визардом поиска, пагинацией, подписками и плановыми уведомлениями
- APScheduler для периодического парсинга (каждые 12 часов по умолчанию)
- Ротация логов для приложения и бота

## Стек

| Слой | Технология |
|---|---|
| Язык | Python 3.12 |
| Backend | FastAPI + uvicorn |
| БД | PostgreSQL 16 + SQLAlchemy 2.0 async |
| Миграции | Alembic |
| Валидация | Pydantic v2 + pydantic-settings |
| HTTP-клиент | httpx (async) |
| Планировщик | APScheduler 3.x (AsyncIOScheduler) |
| Экспорт | pandas + openpyxl |
| Инфраструктура | Docker Compose |
| Бот | aiogram 3.x |

## Источники данных

### Vuokraovi (vuokraovi.com)

~10 800 объявлений. Двухшаговый REST API: страница листинга → детали по `friendlyId`.

- Фильтрует объявления SATO по `office.customerGroupId == 26`
- Извлекает включение воды/электричества из структурированных полей `periodicCharges` с regex fallback
- Извлекает статус ARA и студенческого жилья из `residenceDetailsDTO.livingFormType`
- Извлекает планировку, подрайон и информацию об арендодателе из детального ответа
- Параллельная загрузка деталей через `asyncio.Semaphore(concurrency=10)` (~15 мин против ~5 часов последовательно)

### SATO (sato.fi)

~930 объявлений. Одношаговый fetch из эндпоинта `searchV2`. Охватывает Хельсинки, Эспоо и Вантаа (три отдельных запроса).

- Извлекает статус ARA и студенческого жилья из `apartment.flags.isAra` / `flags.studentHome`

## API эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/listings/parse` | Запустить парсинг Vuokraovi + SATO, сохранить в БД |
| `GET` | `/listings/` | Список объявлений с фильтрами |
| `GET` | `/listings/export` | Экспорт в Excel (.xlsx) |

### Параметры фильтрации (GET /listings/)

`price_min`, `price_max`, `area_min`, `area_max`, `district`, `room_count`, `water_included`, `electricity_included`, `is_private_lessor`, `is_ara`, `is_student_home`, `source`, `limit`, `offset`

## Модель базы данных

### Listing

| Колонка | Тип | Примечание |
|---|---|---|
| `external_id` | `String(50)` | Уникальный ID в источнике |
| `source` | `String(20)` | `vuokraovi` или `sato` |
| `url` | `String(500)` | Ссылка на объявление |
| `price` | `Float` | €/мес |
| `area` | `Float` | м² |
| `district` | `String(200)` | Район |
| `address` | `String(300)` | Адрес с этажом |
| `room_count` | `String(30)` | напр. `TWO_ROOMS` |
| `room_structure` | `String(150)` | Финская нотация, напр. `2h+kk` |
| `water_included` | `Boolean` | `null` если неизвестно |
| `water_price` | `Float` | €/мес если не включена |
| `electricity_included` | `Boolean` | `null` если неизвестно |
| `floor_plan_url` | `String(1000)` | |
| `available_from` | `String(50)` | `IMMEDIATELY` или дата ISO |
| `lessor_name` | `String(250)` | |
| `is_private_lessor` | `Boolean` | |
| `is_ara` | `Boolean` | `null` если неизвестно |
| `is_student_home` | `Boolean` | `null` если неизвестно |
| `published_at` | `TIMESTAMP(tz)` | |
| `is_active` | `Boolean` | `False` когда объявление исчезает |

Уникальное ограничение: `uq_source_external_id (source, external_id)`

### UserFilter

Хранит фильтры подписки пользователя: цена, площадь, районы, количество комнат, вода/электричество, тип арендодателя, ARA, студенческое жильё, источник.

### SeenListing

Отслеживает, какие объявления уже были отправлены пользователю, для исключения дублей в уведомлениях.

## 🚀 Запуск

### 1. Клонирование

```bash
git clone https://github.com/<your-username>/helsinki-rental-parser.git
cd helsinki-rental-parser
```

### 2. Настройка окружения

```bash
cp .env.example .env
```

Заполнить .env

### 3. Сборка

```bash
docker compose build
```

### 4. Запуск

```bash
docker compose up -d
```

Миграции применяются автоматически при старте.

### Документация API

Доступна по адресу `http://localhost:8000/docs` после запуска.

## Конфигурация

| Переменная | По умолчанию | Описание |
|---|---|---|
| `APP_DB__URL` | — | Строка подключения PostgreSQL |
| `APP_BOT__TOKEN` | — | Токен Telegram-бота |
| `APP_PARSER__REQUEST_DELAY_SECONDS` | `1.5` | Задержка между запросами |
| `APP_PARSER__CONCURRENCY` | `10` | Параллельных запросов деталей (Vuokraovi) |
| `APP_PARSER__CHECK_INTERVAL_MINUTES` | `720` | Интервал планировщика (12 часов) |
| `APP_PARSER__NOTIFICATION_LIMIT` | `50` | Макс. объявлений за цикл уведомлений на пользователя |
| `APP_VUOKRAOVI__SATO_CUSTOMER_GROUP_ID` | `26` | ID группы клиентов для фильтрации SATO из Vuokraovi |

## Расширение

Дополнительные источники с аналогичным REST API, которые можно интегрировать:

- [Lumo](https://lumo.fi) — крупная финская компания по аренде жилья
- [Oikotie Asunnot](https://asunnot.oikotie.fi) — крупный финский портал недвижимости

## Авторские права и участие

### Автор проекта:
Natalia Levant
GitHub: https://github.com/NVLev

### Авторские права:
© 2026 Natalia Levant
Проект опубликован в образовательных и исследовательских целях.
Разрешено использование кода в некоммерческих проектах с обязательной ссылкой на авторов.
Для коммерческого использования требуется согласование с правообладателями.
