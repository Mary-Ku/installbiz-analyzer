"""Модуль слоя доступа к данным."""

from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Text, func, insert, select
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


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Возвращает асинхронную сессию базы данных."""
    async with async_session_maker() as session:
        yield session


class FileDAO:
    """Класс для работы с файлами в SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Сохраняет объект асинхронной сессии."""
        self._session = session

    async def count(self) -> int:
        """Возвращает количество файлов в базе."""
        query = select(func.count()).select_from(File)
        res = await self._session.execute(query)
        return res.scalar_one()

    async def get_page(
        self,
        page: int,
        per_page: int,
        newest_first: bool,
    ) -> tuple[Sequence[File], int]:
        """Возвращает страницу файлов и их общее количество."""
        order_column = File.downloaded_at.desc() if newest_first else File.downloaded_at.asc()
        query = (
            select(File)
            .order_by(order_column, File.id)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        res = await self._session.execute(query)
        return res.scalars().all(), await self.count()

    async def get_by_ids(
        self,
        file_ids: list[int] | None,
        exclude_ids: list[int] | None = None,
    ) -> Sequence[File]:
        """Возвращает файлы по списку id или все (кроме exclude_ids), если список не передан."""
        query = select(File).order_by(File.id)
        if file_ids is not None:
            query = query.where(File.id.in_(file_ids))
        if exclude_ids:
            query = query.where(File.id.notin_(exclude_ids))
        res = await self._session.execute(query)
        return res.scalars().all()

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
