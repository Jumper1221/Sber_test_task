# Сервис платежей (Sber Test Task)

## Описание

Асинхронный сервис для создания и подтверждения платежей с аутентификацией пользователей, реализованный на FastAPI и PostgreSQL. Предназначен для тестового задания Junior Python Developer.

## Стек технологий

- **Backend**: FastAPI (Python 3.11+)
- **База данных**: PostgreSQL
- **ORM**: SQLAlchemy + Pydantic
- **Аутентификация**: JWT
- **Контейнеризация**: Docker, Docker Compose
- **Миграции**: Alembic
- **Тесты**: Pytest

## Функционал

- Регистрация и вход пользователей (JWT)
- Создание платежа (сумма, карта, ФИО, статус)
- Подтверждение/отмена платежа (с изменением баланса)
- Получение списка платежей пользователя
- Логирование событий
- Swagger UI для документации

## Быстрый старт

1. **Клонируйте репозиторий:**
	```powershell
	git clone <repo_url>
	cd Sber_test_task
	```

2. **Настройте переменные окружения:**
	- Скопируйте `.env.example` в `.env` и заполните параметры PostgreSQL.

3. **Запустите сервис:**
	```powershell
	docker-compose up
	```
	Сервис будет доступен на [http://localhost:8000](http://localhost:8000)

4. **Документация API:**
	- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
	- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Структура проекта

```
├── app/
│   ├── main.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   ├── core/
│   └── utils/
├── alembic/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```

## Дополнительно

- Миграции реализованы отдельным контейнером в докере
- Логи: `docker logs <container_name>`
- Возможна интеграция с Celery/Redis, mock-платежным шлюзом, CI/CD.

