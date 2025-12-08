import logging

import strawberry
from fastapi.responses import JSONResponse, PlainTextResponse
from strawberry.fastapi import GraphQLRouter

from src import create_app
from src.adapters.graphql_adapters.query import Query

logger = logging.getLogger(__name__)
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
