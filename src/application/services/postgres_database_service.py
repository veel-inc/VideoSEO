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
from pathlib import Path
from typing import Any, Dict, List

from src.domain.models import VideoSEOResponseModel
from src.ports.output.postgres_database_port import PostgresDatabasePort

logger = logging.getLogger(__name__)


class PostgresDatabaseService:
    def __init__(self, database_port: PostgresDatabasePort):
        self.database_port = database_port

    async def initialize_database_schema(self) -> None:
        """Initialize all required database tables"""
        logger.info("Initializing database schema")
        self.database_port.create_table("videos")
        self.database_port.create_table("video_segments")
        logger.info("Database schema initialized successfully")

    async def store_video_data(self, parquet_file_path: str | Path) -> None:
        """Store video data from a Parquet file into the database.
        Args:
            parquet_file_path (str | Path): Path to the .parquet file to read and insert into the database.
        Returns:
            None
        """
        try:
            file_path = Path(parquet_file_path)

            if not file_path.exists():
                raise FileNotFoundError(f"Parquet file not found: {parquet_file_path}")

            if file_path.suffix != ".parquet":
                raise ValueError(f"Expected .parquet file, got: {file_path.suffix}")

            logger.info(f"Storing data from: {parquet_file_path}")
            await self.database_port.bulk_insert_from_parquet(
                parquet_file_path=parquet_file_path
            )
            logger.info("Successfully stored data from parquet file")
        except Exception as e:
            logger.error(f"Unexpected error occured while storing parquet file: {e}")
            raise

    async def search_video_segments(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        similarity_alogrithm: str = "cosine",
    ) -> List[Dict[str, Any]]:
        """
        Search for similar video segments using a query embedding.
        Args:
            query_embedding (List[float]): Embedding vector representing the query; must be non-empty.
            top_k (int): Maximum number of similar segments to return (must be positive). Defaults to 10.
            similarity_alogrithm (str): Similarity algorithm to use (e.g., "cosine"). Defaults to "cosine".
        Returns:
            List[Dict[str, Any]]: A list of serialized dictionaries representing matching video segments,
            validated and cleaned (None values excluded).
        """

        if not query_embedding:
            raise ValueError("Query embedding cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be positive")

        logger.info(f"Searchig for top {top_k} similar segments")
        results = await self.database_port.search_similar_vectors(
            query_embedding=query_embedding,
            top_k=top_k,
            similarity_algorithm=similarity_alogrithm,
        )

        logger.info(f"Found {len(results)} matching segments")
        # return results
        schema = VideoSEOResponseModel.model_validate(results).model_dump(
            exclude_none=True
        )
        return schema

    async def cleanup(self) -> None:
        """Close databse connections and cleanup resources"""
        logger.info("Cleaning up service resources")
        await self.database_port.close()
