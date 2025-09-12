import pytest
from httpx import AsyncClient

# Помечаем все тесты в этом файле как асинхронные
pytestmark = pytest.mark.asyncio


@pytest.mark.asyncio(loop_scope="class")
@pytest.mark.order(1)  # Указываем порядок выполнения
class TestAuthWorkflow:
    """Класс для тестирования полного цикла аутентификации."""

    async def test_registration(self, class_client: AsyncClient, workflow_state: dict):
        """Тест 1: Регистрация. Данные сохранятся в БД."""
        user_data = {
            "username": "workflow_user",
            "email": "workflow@example.com",
            "password": "strong_password123",
        }
        # Сохраняем данные в общий словарь
        workflow_state["user_data"] = user_data

        response = await class_client.post(
            "/auth/register",
            json={**user_data, "password_repeat": user_data["password"]},
        )
        assert response.status_code == 200, response.text

        # Обновляем словарь, добавляя id
        workflow_state["user_data"]["id"] = response.json().get("id")
        assert workflow_state["user_data"]["id"] is not None

    @pytest.mark.order(2)
    async def test_login(self, class_client: AsyncClient, workflow_state: dict):
        """Тест 2: Логин. Берем данные из фикстуры и сохраняем токен."""
        assert "user_data" in workflow_state, "User data not found in state"
        user_data = workflow_state["user_data"]

        response = await class_client.post(
            "/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
            },
        )
        assert response.status_code == 200, response.text

        token_data = response.json()
        assert "access_token" in token_data

        # Сохраняем токен в общий словарь
        workflow_state["access_token"] = token_data["access_token"]

    @pytest.mark.order(3)
    async def test_get_self_profile(
        self, class_client: AsyncClient, workflow_state: dict
    ):
        """Тест 3: Проверка эндпоинта. Берем токен из фикстуры."""
        assert "access_token" in workflow_state, "Access token not found in state"
        access_token = workflow_state["access_token"]
        user_data = workflow_state["user_data"]

        headers = {"Authorization": f"Bearer {access_token}"}
        response = await class_client.get("/users/me", headers=headers)

        assert response.status_code == 200, response.text
        profile_data = response.json()
        assert profile_data["email"] == user_data["email"]
        assert profile_data["username"] == user_data["username"]
        assert profile_data["id"] == user_data["id"]
        assert profile_data["balance"] == "0.00"
