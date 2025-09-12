import pytest
from httpx import AsyncClient

# Помечаем все тесты в этом файле как асинхронные
pytestmark = pytest.mark.asyncio


async def test_registration(client: AsyncClient):
    """Тестируем регистрацию пользователя через API."""

    response = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "securepassword",
            "password_repeat": "securepassword",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("id") is not None
    assert data.get("username") == "testuser"
    assert data.get("email") == "testuser@example.com"


async def test_login(client: AsyncClient):
    """Тестируем вход пользователя через API."""

    # Сначала регистрируем пользователя
    response_register = await client.post(
        "/auth/register",
        json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "securepassword",
            "password_repeat": "securepassword",
        },
    )

    user_id = response_register.json().get("id")
    assert response_register.status_code == 200
    print("Registered user ID:", user_id)

    # Затем пытаемся войти
    response = await client.post(
        "/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "securepassword",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("access_token") is not None
    assert data.get("token_type") == "bearer"
    assert data.get("user") is not None
    assert data["user"].get("username") == "testuser"
    assert data["user"].get("email") == "testuser@example.com"
    assert data["user"].get("id") == user_id
