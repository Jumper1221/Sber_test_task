import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.core.wait_strategies import LogMessageWaitStrategy
from testcontainers.postgres import PostgresContainer

from app.core.db import Base, get_async_session
from app.main import app as fastapi_app

# URL тестовой базы данных, вынести в настройки
# DB_URL = "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"


@pytest.fixture(scope="session")
def postgres_container():
    """Запускает контейнер Postgres и ждет его готовности."""
    # Создаем экземпляр контейнера
    postgres = PostgresContainer("postgres:16")

    postgres.waiting_for(
        LogMessageWaitStrategy(
            r"database system is ready to accept connections", times=1
        )
    )

    # Запускаем контейнер через менеджер контекста
    with postgres as container:
        yield container


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_container: PostgresContainer):
    """Создаёт асинхронный движок SQLAlchemy для тестов."""
    # Получаем URL из контейнера
    postgres_url = postgres_container.get_connection_url()

    # Надежно заменяем драйвер на асинхронный
    url = postgres_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")

    engine = create_async_engine(url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database(engine):
    """Создаёт таблицы перед тестами и удаляет после."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Фикстура, которая создает новую сессию для КАЖДОГО теста
@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Открывает транзакцию для теста и откатывает её после."""
    async with engine.connect() as connection:
        trans = await connection.begin()
        async_session = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            yield session
        await trans.rollback()


# Фикстура, которая создает одну сессию для ВСЕГО тестового класса
@pytest_asyncio.fixture(scope="class")
async def class_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Создает одну транзакцию для всего тестового класса.
    В конце коммитит изменения, если все тесты в классе прошли.
    """
    async with engine.connect() as connection:
        trans = await connection.begin()
        async_session = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with async_session() as session:
            yield session

        # ВАЖНО: Вместо отката мы можем сделать коммит,
        # но обычно для тестов даже этого не нужно.
        # Транзакция просто закроется. Для явности можно оставить откат,
        # если не нужно сохранять данные после всего класса.
        # Если нужно, чтобы данные СОХРАНИЛИСЬ для следующего класса,
        # то используйте commit(). В нашем случае rollback() в конце - это ОК.
        await trans.rollback()  # Откатим все после выполнения всех тестов класса


@pytest.fixture(scope="class")
def class_app(class_session: AsyncSession) -> FastAPI:
    """Предоставляет приложение с сессией, живущей на протяжении класса."""

    def override_get_session():
        yield class_session

    fastapi_app.dependency_overrides[get_async_session] = override_get_session
    return fastapi_app


@pytest_asyncio.fixture(scope="class")
async def class_client(class_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Предоставляет HTTP-клиент для классовых тестов."""
    async with AsyncClient(
        transport=ASGITransport(app=class_app), base_url="http://test"
    ) as client:
        yield client


# Фикстура, которая предоставляет наше приложение
@pytest.fixture(scope="function")
def app(session: AsyncSession) -> FastAPI:
    # Для каждого теста мы подменяем зависимость get_async_session
    # на функцию, которая возвращает нашу тестовую сессию
    def override_get_session():
        yield session

    fastapi_app.dependency_overrides[get_async_session] = override_get_session
    return fastapi_app


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Фикстура клиента чтобы для каждого теста
# создавался новый клиент с новой подменой зависимости
@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.fixture(scope="class")
def workflow_state() -> dict:
    """Простой словарь для обмена состоянием между тестами в одном классе."""
    return {}
