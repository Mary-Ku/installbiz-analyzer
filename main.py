"""Точка входа в приложение InstallBiz Analyzer."""

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.download import download_service
from app.download import router as download_router
from app.files import router as files_router
from app.stats import router as stats_router

BASE_DIR = Path(__file__).resolve().parent


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


@app.middleware('http')
async def no_cache_static(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Отключает кэширование статики, чтобы браузер всегда брал свежие файлы."""
    response = await call_next(request)
    if request.url.path.startswith('/static'):
        response.headers['Cache-Control'] = 'no-cache'
    return response


templates = Jinja2Templates(directory=BASE_DIR / 'app' / 'templates')

app.include_router(download_router, prefix='/api/download')
app.include_router(files_router, prefix='/api/files')
app.include_router(stats_router, prefix='/api/stats')
app.mount('/static', StaticFiles(directory=BASE_DIR / 'static'), name='static')


@app.get('/', response_class=HTMLResponse)
async def home_page(request: Request) -> HTMLResponse:
    """Главная страница приложения."""
    return templates.TemplateResponse(request=request, name='index.html')


if __name__ == '__main__':
    uvicorn.run('main:app', host=settings.HTTP_HOST, port=settings.HTTP_PORT)
