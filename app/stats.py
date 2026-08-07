"""Модуль расчёта статистики по цифрам в содержимом файлов."""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import File, FileDAO, get_session

router = APIRouter()

_DIGITS = tuple('0123456789')


class StatsRequest(BaseModel):
    """Схема запроса расчёта статистики (file_ids=None — все файлы)."""

    file_ids: list[int] | None = None


class FileStats(BaseModel):
    """Схема статистики по одному файлу."""

    file_id: int
    file_name: str
    counts: dict[str, int]


class StatsResponse(BaseModel):
    """Схема результата расчёта: пофайловая статистика и итог."""

    total: dict[str, int]
    files: list[FileStats]


def count_digits(content: str) -> dict[str, int]:
    """Считает, сколько раз каждая цифра 0-9 встречается в тексте."""
    counts = dict.fromkeys(_DIGITS, 0)
    for char in content:
        if char in counts:
            counts[char] += 1
    return counts


def calculate_stats(files: Sequence[File]) -> StatsResponse:
    """Производит расчёт пофайловой и общей статистики по цифрам."""
    total = dict.fromkeys(_DIGITS, 0)
    files_stats = []

    for file in files:
        counts = count_digits(file.content)
        files_stats.append(FileStats(file_id=file.id, file_name=file.name, counts=counts))
        for digit in _DIGITS:
            total[digit] += counts[digit]

    return StatsResponse(total=total, files=files_stats)


@router.post('')
async def calculate_stats_endpoint(
    stats_request: StatsRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StatsResponse:
    """Производит расчёт статистики по выбранным файлам (или по всем)."""
    files = await FileDAO(session).get_by_ids(stats_request.file_ids)
    return calculate_stats(files)
