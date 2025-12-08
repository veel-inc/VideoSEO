# Copyright (C) 2025 Veel Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

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
