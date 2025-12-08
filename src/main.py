import logging
import os
from contextlib import asynccontextmanager

import strawberry
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from strawberry.fastapi import GraphQLRouter

from infrastructure import MaterializedViewRefreshScheduler
from infrastructure.scheduler import TrendingSearchScheduler
from src.adapters import AsyncPostgresDatabaseAdapter
from src.adapters.graphql_adapters.query import Query

logger = logging.getLogger(__name__)
from src.core import setup_opentelemetry_and_logger

load_dotenv()

_trending_scheduler = None
_mv_scheduler = None
_db_adapter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown of trending search system.
    """
    global _trending_scheduler
    global _mv_scheduler
    global _db_adapter

    # Startup
    logger.info("Application startup: Initializing trending search")

    try:
        _db_adapter = AsyncPostgresDatabaseAdapter()
        _trending_scheduler = TrendingSearchScheduler(
            interval_minutes=int(os.getenv("INTERVAL_MINUTES", 5))
        )
        _trending_scheduler.start()

        logger.info("Trending search system initialized")

        _mv_scheduler = MaterializedViewRefreshScheduler(
            database_adapter=_db_adapter,
            interval_minutes=int(os.getenv("MATERIALIZED_VIEW_REFRESH_INTERVAL", 15)),
        )
        _mv_scheduler.start()
        logger.info("Materialized view scheduler initialized")

        yield

    finally:
        # Shutdown
        logger.info("Application shutdown: Stopping trending search")

        if _trending_scheduler and _trending_scheduler.is_running:
            _trending_scheduler.stop()

        logger.info("Trending search system stopped")

        if _mv_scheduler and _mv_scheduler.is_running:
            _mv_scheduler.stop()
        logger.info("Materialized view scheduler stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Video SEO API",
        description="API for video search and trending analysis",
        version="1.0.0",
        lifespan=lifespan,
    )
    setup_opentelemetry_and_logger(app, service_name="nuvia")
    return app


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema=schema)
app = create_app()

app.include_router(graphql_app, prefix="/graphql")


@app.get("/ping")
def ping():
    return JSONResponse(status_code=200, content="OK!")


@app.get("/graphql/schema.graphql")
def get_graphql_schema():
    return PlainTextResponse(schema.as_str(), media_type="text/plain")
