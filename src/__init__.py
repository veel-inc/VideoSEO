from fastapi import FastAPI

from src.core import setup_opentelemetry_and_logger


def create_app() -> FastAPI:
    app = FastAPI()
    setup_opentelemetry_and_logger(app, service_name="nuvia")
    return app
