"""Содержит конфигурационные настройки проекта."""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

LOGGER = logging.getLogger('installbiz-analyzer')


class BaseConfig:
    """Базовый класс конфигурации приложения."""

    HTTP_HOST = os.getenv('HTTP_HOST', 'localhost')
    HTTP_PORT = int(os.getenv('HTTP_PORT', '8000'))

    POSTGRES_HOST = os.getenv('POSTGRES_HOST', '127.0.0.1')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')
    POSTGRES_DB_NAME = os.getenv('POSTGRES_DB_NAME', 'installbiz_analyzer')

    SQLALCHEMY_DATABASE_URI = (
        f'postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}'
        f'@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB_NAME}'
    )

    EXTERNAL_API_BASE_URL = os.getenv('EXTERNAL_API_BASE_URL', 'http://91.199.149.128:18001')
    CANDIDATE_ID = os.getenv('CANDIDATE_ID', 'some_user')

    # Часовой пояс для отображения времени (Новосибирск, UTC+7)
    LOCAL_TIMEZONE = 'Asia/Novosibirsk'


settings = BaseConfig()
