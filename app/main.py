import logging
from contextlib import asynccontextmanager
from logging.config import dictConfig

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.utils.lg import logging_config

dictConfig(logging_config)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup...")
    yield 
    logger.info("Application shutdown...")


app = FastAPI(
    title="Сервис платежей",
    description="API для управления платежами и транзакциями",
    version="0.0.1", 
    root_path="/api",  
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
