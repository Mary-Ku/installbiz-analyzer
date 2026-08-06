"""Содержит конфигурационные настройки проекта."""

import os

from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    """Базовый класс конфигурации приложения."""

    POSTGRES_HOST = os.getenv('POSTGRES_HOST', '127.0.0.1')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')
    POSTGRES_DB_NAME = os.getenv('POSTGRES_DB_NAME', 'installbiz_analyzer')

    SQLALCHEMY_DATABASE_URI = (
        f'postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}'
        f'@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB_NAME}'
    )


settings = BaseConfig()
