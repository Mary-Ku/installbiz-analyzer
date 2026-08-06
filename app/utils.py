"""Содержит вспомогательные функции для запросов к сторонним API."""

import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps

from httpx import HTTPStatusError, TransportError, codes

from app.config import LOGGER
from app.exceptions import RequestFailedError

# Лимит попыток запроса при транзиентных ошибках (сеть, 5xx)
_MAX_REQUEST_RETRIES = 3

# Лимит повторов запроса при ответах 429 подряд
_MAX_RATE_LIMIT_RETRIES = 10

# Пауза между попытками в секундах
DEFAULT_RETRY_DELAY = 5.0


def retry_request[**Params, Result](
    method: Callable[Params, Awaitable[Result]],
) -> Callable[Params, Awaitable[Result]]:
    """Повторяет запрос после 429 и при транзиентных ошибках."""

    @wraps(method)
    async def wrapper(*args: Params.args, **kwargs: Params.kwargs) -> Result:
        """Выполняет запрос с паузами между попытками."""
        attempt = 0
        rate_limit_retries = 0
        while attempt < _MAX_REQUEST_RETRIES:
            try:
                return await method(*args, **kwargs)
            except RequestFailedError as exc:
                if exc.status_code != codes.TOO_MANY_REQUESTS:
                    raise

                rate_limit_retries += 1
                if rate_limit_retries == _MAX_RATE_LIMIT_RETRIES:
                    raise
                LOGGER.warning('Превышен лимит запросов, пауза %.0f сек.', exc.retry_after)
                await asyncio.sleep(exc.retry_after)
            except (TransportError, HTTPStatusError) as exc:
                if (
                    isinstance(exc, HTTPStatusError)
                    and exc.response.status_code < codes.INTERNAL_SERVER_ERROR
                ):
                    raise
                attempt += 1
                if attempt == _MAX_REQUEST_RETRIES:
                    raise
                LOGGER.warning(
                    'Ошибка запроса (%s), повтор %s/%s через %.0f сек.',
                    exc,
                    attempt + 1,
                    _MAX_REQUEST_RETRIES,
                    DEFAULT_RETRY_DELAY,
                )
                await asyncio.sleep(DEFAULT_RETRY_DELAY)
        msg = 'Цикл повторов завершился без результата и без исключения.'
        raise AssertionError(msg)

    return wrapper
