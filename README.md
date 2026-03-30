
## Структура проекта

```
helsinki-rental-parser/
│
├── app/                    # FastAPI backend
│   ├── api/
│   ├── parsers/
│   ├── services/
│   └── database/
│
├── bot/                    # Telegram bot
│   ├── handlers/
│   ├── keyboards/
│   ├── services/
│   └── filters/
│
├── migrations/
├── config.py               # общий конфиг — db, parser, vuokraovi, sato, bot
├── main_app.py
├── main_bot.py
├── docker-compose.yml
├── .env
├── .env.template
└── README.md
```

