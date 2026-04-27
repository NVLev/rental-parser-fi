FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* ./

RUN poetry install --only main --no-root --no-interaction

RUN mkdir -p /app/logs

COPY . .