"""Модуль API скачанных файлов."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import FileDAO, get_session

router = APIRouter()


class FileResponse(BaseModel):
    """Схема данных для чтения файла."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    downloaded_at: datetime


class FilePage(BaseModel):
    """Схема страницы со списком файлов."""

    files: list[FileResponse]
    total: int
    page: int
    per_page: int


@router.get('')
async def get_files_endpoint(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 20,
    order: Literal['asc', 'desc'] = 'desc',
) -> FilePage:
    """Возвращает страницу файлов с сортировкой по времени скачивания."""
    files, total = await FileDAO(session).get_page(
        page=page,
        per_page=per_page,
        newest_first=order == 'desc',
    )
    return FilePage(
        files=[FileResponse.model_validate(file) for file in files],
        total=total,
        page=page,
        per_page=per_page,
    )
