"""Модуль фонового скачивания каталога файлов из внешнего API."""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from io import BytesIO
from zipfile import ZipFile
from zoneinfo import ZoneInfo

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from httpx import AsyncClient, Response, codes
from pydantic import BaseModel

from app.config import LOGGER, settings
from app.database import FileDAO, async_session_maker
from app.exceptions import NoDownloadProgressError, RequestFailedError
from app.utils import DEFAULT_RETRY_DELAY, retry_request

_DOWNLOAD_BATCH_SIZE = 3
_MIN_REQUEST_INTERVAL = 1.0
_NSK_TZ = ZoneInfo(settings.LOCAL_TIMEZONE)


class DownloadStatusResponse(BaseModel):
    """Схема состояния фонового процесса скачивания."""

    is_running: bool = False
    started_at: datetime | None = None
    received_names: int = 0
    downloaded_files: int = 0
    files_in_db: int = 0
    message: str | None = None


class ExternalApiClient:
    """Асинхронный клиент внешнего API скачивания файлов."""

    def __init__(self, client: AsyncClient | None = None) -> None:
        """Создаёт клиент с заголовком идентификации кандидата."""
        headers = {'X-Candidate-Id': settings.CANDIDATE_ID}
        self._client = client or AsyncClient(
            base_url=settings.EXTERNAL_API_BASE_URL,
            headers=headers,
            timeout=30.0,
        )
        self._last_request_at = 0.0

    async def aclose(self) -> None:
        """Закрывает пул соединений HTTP-клиента."""
        await self._client.aclose()

    async def get_names(self) -> list[str]:
        """Возвращает имена ещё не скачанных файлов."""
        response = await self._request('GET', '/api/files/names')
        return list(response.json()['file_names'])

    async def download_files(self, file_names: list[str]) -> bytes:
        """Скачивает файлы по именам (не более 3) и возвращает ZIP-архив байтами."""
        response = await self._request(
            'POST',
            '/api/files/download',
            json={'file_names': file_names},
        )
        return response.content

    async def mark_downloaded(self, file_names: list[str]) -> None:
        """Отмечает файлы скачанными во внешнем API."""
        await self._request(
            'POST',
            '/api/files/downloaded',
            json={'file_names': file_names},
        )

    @retry_request
    async def _request(self, method: str, url: str, **kwargs: object) -> Response:
        """Выполняет запрос с учётом лимитов внешнего API."""
        # Минимальная пауза между запросами, чтобы не превысить лимит внешнего API
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < _MIN_REQUEST_INTERVAL:
            await asyncio.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()

        response = await self._client.request(method, url, **kwargs)  # type: ignore[arg-type]

        if response.status_code in (codes.TOO_MANY_REQUESTS, codes.FORBIDDEN):
            raise RequestFailedError(response.status_code, _parse_retry_after(response))

        response.raise_for_status()
        return response


def _parse_retry_after(response: Response) -> float:
    """Извлекает время паузы в секундах из заголовка Retry-After."""
    header = response.headers.get('Retry-After')
    if header is None:
        return DEFAULT_RETRY_DELAY

    if header.isdigit():
        return float(header)

    # Заголовок может содержать HTTP-дату вместо количества секунд
    try:
        retry_at = parsedate_to_datetime(header)
    except (TypeError, ValueError):
        return DEFAULT_RETRY_DELAY

    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=UTC)
    return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())


class DownloadService:
    """Сервис фонового скачивания каталога файлов."""

    def __init__(self, client: ExternalApiClient | None = None) -> None:
        """Создаёт сервис с клиентом внешнего API."""
        self._client = client or ExternalApiClient()
        self._status = DownloadStatusResponse()
        self._task: asyncio.Task[None] | None = None

    @property
    def status(self) -> DownloadStatusResponse:
        """Возвращает текущее состояние процесса скачивания."""
        return self._status

    async def shutdown(self) -> None:
        """Освобождает ресурсы сервиса."""
        await self._client.aclose()

    def start(self) -> bool:
        """Запускает скачивание в фоне, возвращает False, если оно уже идёт."""
        if self._task is not None and not self._task.done():
            return False

        self._status = DownloadStatusResponse(
            is_running=True,
            started_at=datetime.now(_NSK_TZ),
        )
        self._task = asyncio.create_task(self._run())
        return True

    async def _run(self) -> None:
        """Выполняет скачивание каталога и обновляет статус по итогу."""
        try:
            await self._download_catalog()
        except RequestFailedError as exc:
            if exc.status_code == codes.FORBIDDEN:
                blocked_until = datetime.now(_NSK_TZ) + timedelta(seconds=exc.retry_after)
                self._status.message = (
                    'Внешнее API заблокировало запросы, '
                    f'разблокировка в {blocked_until:%H:%M:%S} по НСК. '
                    'Процесс остановлен, скачанные файлы сохранены.'
                )
            else:
                self._status.message = 'Процесс остановлен из-за ошибки, подробности в логах.'
            LOGGER.warning('%s (%s)', self._status.message, exc)
        except NoDownloadProgressError:
            self._status.message = (
                'Внешний API не возвращает содержимое запрошенных файлов. Процесс остановлен.'
            )
            LOGGER.warning(self._status.message)
        else:
            self._status.message = 'Каталог скачан полностью.'
            LOGGER.info('Загрузка завершена: получено %s файлов', self._status.downloaded_files)

        self._status.is_running = False

    async def _download_catalog(self) -> None:
        """Скачивает каталог файлов порциями, пока не останется нескачанных."""
        async with async_session_maker() as session:
            dao = FileDAO(session)

            while names := await self._client.get_names():
                self._status.received_names += len(names)

                # Уже сохранённые файлы не скачиваем повторно,
                # но отмечаем скачанными, чтобы они ушли из выдачи
                existing_names = await dao.get_existing_names(names)
                handled_count = 0
                for batch in _batches(names, _DOWNLOAD_BATCH_SIZE):
                    saved_count, marked_count = await self._download_batch(
                        dao,
                        batch,
                        existing_names,
                    )
                    self._status.downloaded_files += saved_count
                    handled_count += marked_count

                if handled_count == 0:
                    # Ни один файл не сохранён и не отмечен: API не отдаёт содержимое
                    raise NoDownloadProgressError

    async def _download_batch(
        self,
        dao: FileDAO,
        batch: list[str],
        existing_names: set[str],
    ) -> tuple[int, int]:
        """Скачивает порцию файлов, возвращает числа сохранённых и отмеченных имён."""
        new_names = [name for name in batch if name not in existing_names]
        saved_names: set[str] = set()
        if new_names:
            archive = await self._client.download_files(new_names)
            files = _unpack_zip(archive)
            saved_names = set(files)

            missing_names = [name for name in new_names if name not in files]
            if missing_names:
                LOGGER.error('Внешний API не вернул содержимое файлов: %s', missing_names)
            await dao.add_many(files)

        # Сначала коммитим файлы в базу и только потом отмечаем их скачанными:
        # иначе при падении между отметкой и коммитом файлы потеряются
        await dao.commit()

        # Отмечаем только реально сохранённые файлы: иначе отсутствующие
        # в архиве файлы уйдут из выдачи, не попав в базу
        handled_names = [
            name for name in batch if name in existing_names or name in saved_names
        ]
        if handled_names:
            await self._client.mark_downloaded(handled_names)
        return len(saved_names), len(handled_names)


def _batches(names: list[str], size: int) -> list[list[str]]:
    """Разбивает список имён на порции заданного размера."""
    return [names[start : start + size] for start in range(0, len(names), size)]


def _unpack_zip(archive: bytes) -> dict[str, str]:
    """Распаковывает ZIP-архив в словарь (имя файла -> содержимое)."""
    with ZipFile(BytesIO(archive)) as zip_file:
        return {name: zip_file.read(name).decode('utf-8') for name in zip_file.namelist()}


download_service = DownloadService()

router = APIRouter()


@router.post('/start')
async def start_download_endpoint() -> JSONResponse:
    """Запускает фоновое скачивание каталога файлов."""
    if not download_service.start():
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={'detail': 'Скачивание уже выполняется.'},
        )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={'detail': 'Скачивание запущено.'},
    )


@router.get('/status')
async def get_download_status_endpoint() -> DownloadStatusResponse:
    """Возвращает текущее состояние процесса скачивания."""
    async with async_session_maker() as session:
        files_in_db = await FileDAO(session).count()
    return download_service.status.model_copy(update={'files_in_db': files_in_db})
