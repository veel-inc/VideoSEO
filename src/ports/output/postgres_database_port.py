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

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class PostgresDatabasePort(ABC):
    """Abstract class for database in postgres"""

    @abstractmethod
    async def create_table(self, table_name: str) -> None:
        pass

    @abstractmethod
    async def search_similar_vectors(
        self,
        query_embedding: List[float],
        top_k: int = 250,
        similarity_algorithm: str = "cosine",
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in the database"""
        pass

    @abstractmethod
    async def bulk_insert_from_parquet(self, parquet_file_path: str | Path) -> None:
        """Bulk insert data from a parquet file"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close database connection"""
        pass

    @abstractmethod
    async def create_session_table(self) -> None:
        pass

    @abstractmethod
    async def insert_into_session_table(
        self,
        chat_id: str,
        response: List[Dict[str, Any]],
        query: str,
        created_at: datetime,
        temporary_id: Optional[str] = None,
    ) -> None:
        pass

    @abstractmethod
    async def create_trends_table(self) -> None:
        """Ensure the `trending_searches` table exists."""
        pass

    @abstractmethod
    async def ingest_queries(
        self, batch_interval_minutes: Optional[int], max_rows: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Return queries to analyze for trending.

        Args:
            batch_interval_minutes: If an int is provided, return rows within the
                last `batch_interval_minutes`. If None, return historical rows
                (see `max_rows`).
            max_rows: When `batch_interval_minutes` is None, optionally limit the
                number of rows returned to this many most-recent rows.
        """
        pass

    @abstractmethod
    async def persist_trends(
        self, trends: List[Dict[str, Any]], batch_timestamp: datetime
    ) -> None:
        """Persist computed trend records to the database."""
        pass

    @abstractmethod
    async def get_current_trends(
        self, limit: int = 20, min_score: float = 0.0
    ) -> Dict[str, Any]:
        """Retrieve current top trends (formatted) from DB."""
        pass

    @abstractmethod
    async def create_materialized_video_stat_table(self) -> None:
        """Ensure the `materialized_video_stat` table exists."""
        pass

    @abstractmethod
    async def search_popular_videos(self, limit: Optional[int] = 15) -> List:
        """Search for popular videos."""
        pass

    # @abstractmethod
    # async def create_index_for_popular_videos(self):
    #     pass
    @abstractmethod
    async def refresh_materialized_view_tables(self):
        pass
