"""Модуль слоя доступа к данным."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Text, insert, select
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

from app.config import settings

engine = create_async_engine(
    url=settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        """Добавляет 's' в конец имени таблицы в бд."""
        return cls.__name__.lower() + 's'


class File(Base):
    """Модель скачанного файла."""

    name: Mapped[str] = mapped_column(unique=True)
    content: Mapped[str] = mapped_column(Text)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FileDAO:
    """Класс для работы с файлами в SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет объект асинхронной сессии."""
        self._session = session

    async def get_existing_names(self, names: list[str]) -> set[str]:
        """Возвращает имена файлов, которые уже сохранены в базе."""
        if not names:
            return set()
        query = select(File.name).where(File.name.in_(names))
        res = await self._session.execute(query)
        return set(res.scalars().all())

    async def add_many(self, files: dict[str, str]) -> None:
        """Добавляет файлы в базу данных (имя -> содержимое)."""
        if not files:
            return
        downloaded_at = datetime.now(UTC)
        query = insert(File).values(
            [
                {'name': name, 'content': content, 'downloaded_at': downloaded_at}
                for name, content in files.items()
            ],
        )
        await self._session.execute(query)

    async def commit(self) -> None:
        """Фиксирует текущую транзакцию."""
        await self._session.commit()
