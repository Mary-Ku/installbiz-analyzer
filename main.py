"""Точка входа в приложение InstallBiz Analyzer."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.config import settings
from app.download import download_service
from app.download import router as download_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Освобождает ресурсы приложения при остановке."""
    yield
    await download_service.shutdown()


app = FastAPI(
    title='InstallBiz Analyzer',
    description='Сервис скачивания и анализа файлов',
    version='0.1.0',
    lifespan=lifespan,
)

app.include_router(download_router, prefix='/api/download')

if __name__ == '__main__':
    uvicorn.run('main:app', host=settings.HTTP_HOST, port=settings.HTTP_PORT)
