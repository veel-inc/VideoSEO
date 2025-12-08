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
