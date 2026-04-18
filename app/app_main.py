from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.database.db_helper import db_helper
from app.routers import listings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    print("🚀 Приложение запущено. Подключение к БД готово.")
    try:
        yield
    finally:
        await db_helper.dispose()
        print("🔌 Соединение с БД закрыто.")


app = FastAPI(lifespan=lifespan, title="Rental Parser FI")

app.include_router(listings.router)


if __name__ == "__main__":
    uvicorn.run("app_main:app", host="0.0.0.0", port=8000)
