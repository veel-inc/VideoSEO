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

import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, mock_open, patch

import numpy as np
import pandas as pd
import pytest
from psycopg2 import Error, OperationalError

from src.adapters import AsyncPostgresDatabaseAdapter


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for database connection."""
    monkeypatch.setenv("DATABASE_NAME", "test_db")
    monkeypatch.setenv("DATABASE_HOST", "localhost")
    monkeypatch.setenv("DATABASE_PORT", "5432")
    monkeypatch.setenv("DATABASE_USER", "test_user")
    monkeypatch.setenv("DATABASE_PASSWORD", "test_password")


@pytest.fixture
def mock_connection():
    """Create a mock database connection and cursor."""
    mock_conn = MagicMock()
    mock_conn.close = AsyncMock()
    mock_conn.commit = MagicMock()  #
    mock_conn.roll_back = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture
def adapter(mock_env_vars, mock_connection):
    mock_conn, mock_cursor = mock_connection
    adapter = AsyncPostgresDatabaseAdapter(conn=mock_conn)
    adapter.conn = mock_conn
    adapter.cursor = mock_cursor
    return adapter


class TestInitialization:
    """Test suite for adapter initialization."""

    def test_initialization_success(self, mock_env_vars):
        """Test successful initialization with valid credentials."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("psycopg2.connect", return_value=mock_conn):
            adapter = AsyncPostgresDatabaseAdapter()

            assert adapter.dbname == "test_db"
            assert adapter.host == "localhost"
            assert adapter.port == "5432"
            assert adapter.user == "test_user"
            assert adapter.password == "test_password"

    def test_initialization_missing_credentials(self, monkeypatch):
        """Test initialization fails when credentials are missing."""
        monkeypatch.delenv("DATABASE_NAME", raising=False)
        monkeypatch.delenv("DATABASE_HOST", raising=False)
        monkeypatch.delenv("DATABASE_PORT", raising=False)
        monkeypatch.delenv("DATABASE_USER", raising=False)
        monkeypatch.delenv("DATABASE_PASSWORD", raising=False)

        with pytest.raises(ValueError, match="Database Credentials not set"):
            AsyncPostgresDatabaseAdapter()

    def test_initialization_connection_failure(self, mock_env_vars):
        """Test initialization handles connection failures."""
        with patch(
            "psycopg2.connect", side_effect=OperationalError("Connection failed")
        ):
            with pytest.raises(RuntimeError, match="Database connection failed"):
                AsyncPostgresDatabaseAdapter()


class TestExtensionSetup:
    """Test suite for extension setup."""

    def test_setup_single_extension(self, adapter):
        """Test setting up a single extension."""
        adapter._setup_extensions("vector")
        adapter.cursor.execute.assert_called_with(
            'CREATE EXTENSION IF NOT EXISTS "vector";'
        )

    def test_setup_multiple_extensions(self, adapter):
        """Test setting up multiple extensions."""
        adapter._setup_extensions(["vector", "uuid-ossp"])

        calls = adapter.cursor.execute.call_args_list
        assert len(calls) >= 2

    def test_setup_extensions_failure(self, adapter):
        """Test extension setup handles failures."""
        adapter.cursor.execute.side_effect = Exception("Extension error")

        with pytest.raises(Exception, match="Extension error"):
            adapter._setup_extensions("invalid_extension")

        adapter.conn.rollback.assert_called()


class TestCreateTable:
    """Test suite for table creation."""

    @pytest.mark.asyncio
    async def test_create_videos_table(self, adapter):
        """Test creating videos table."""
        await adapter.create_table("videos")

        # Verify SQL was executed
        adapter.cursor.execute.assert_called()
        call_args = adapter.cursor.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS videos" in call_args
        assert "text_embedding VECTOR(1536)" in call_args
        adapter.conn.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_video_segments_table(self, adapter):
        """Test creating video_segments table."""
        await adapter.create_table("video_segments")

        call_args = adapter.cursor.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS video_segments" in call_args
        assert "segment_embedding VECTOR(1536)" in call_args
        adapter.conn.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_table_invalid_name(self, adapter):
        """Test creating table with invalid name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown table name"):
            await adapter.create_table("invalid_table")

    @pytest.mark.asyncio
    async def test_create_table_failure(self, adapter):
        """Test table creation handles failures."""
        adapter.cursor.execute.side_effect = Exception("SQL error")

        with pytest.raises(Exception, match="SQL error"):
            await adapter.create_table("videos")

        adapter.conn.rollback.assert_called()


class TestCreateSessionTable:
    """Test suite for session table creation."""

    @pytest.mark.asyncio
    async def test_create_session_table_success(self, adapter):
        """Test creating session table successfully."""
        await adapter.create_session_table()

        call_args = adapter.cursor.execute.call_args[0][0]
        assert "CREATE TABLE IF NOT EXISTS video_seo_response_history" in call_args
        assert "response JSONB" in call_args
        adapter.conn.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_session_table_failure(self, adapter):
        """Test session table creation handles failures."""
        adapter.cursor.execute.side_effect = Exception("Table creation failed")

        with pytest.raises(Exception):
            await adapter.create_session_table()

        adapter.conn.rollback.assert_called()


class TestInsertIntoSessionTable:
    """Test suite for inserting into session table."""

    @pytest.mark.asyncio
    async def test_insert_session_data(self, adapter):
        """Test inserting response data into session table."""
        test_response = [
            {"question": "test", "answer": "response"},
            {"question": "test2", "answer": "response2"},
        ]

        with patch.object(adapter, "create_session_table") as mock_create:
            with patch.object(adapter, "close") as mock_close:
                await adapter.insert_into_session_table(test_response)

        mock_create.assert_called_once()
        adapter.cursor.execute.assert_called()
        adapter.conn.commit.assert_called()

    @pytest.mark.asyncio
    async def test_insert_session_data_failure(self, adapter):
        """Test insert handles failures."""
        adapter.cursor.execute.side_effect = Exception("Insert failed")

        with patch.object(adapter, "create_session_table"):
            with patch.object(adapter, "close"):
                with pytest.raises(Exception):
                    await adapter.insert_into_session_table([{"test": "data"}])

        adapter.conn.rollback.assert_called()


class TestBulkInsertFromParquet:
    """Test suite for bulk insert from parquet."""

    @pytest.mark.asyncio
    async def test_bulk_insert_video_segments(self, adapter):
        """Test bulk inserting video segments from parquet."""
        # Create test dataframe
        test_df = pd.DataFrame(
            {
                "tenant_id": ["tenant1"],
                "video_id": ["video1"],
                "segment_start_time": [0.0],
                "segment_end_time": [10.0],
                "segment_text": ["test segment"],
                "segment_embedding": [np.array([0.1] * 1536)],
            }
        )

        with patch("pandas.read_parquet", return_value=test_df):
            with patch.object(adapter, "_insert_video_segments") as mock_insert:
                await adapter.bulk_insert_from_parquet("segment_test.parquet")

        mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_insert_videos(self, adapter):
        """Test bulk inserting videos from parquet."""
        test_df = pd.DataFrame(
            {
                "video_id": ["video1"],
                "tenant_id": ["tenant1"],
                "title": ["Test Video"],
                "video_url": ["http://example.com"],
                "video_metadata": [{"key": "value"}],
                "video_text": ["test text"],
                "text_embedding": [np.array([0.1] * 1536)],
            }
        )

        with patch("pandas.read_parquet", return_value=test_df):
            with patch.object(adapter, "_insert_videos") as mock_insert:
                await adapter.bulk_insert_from_parquet("video_test.parquet")

        mock_insert.assert_called_once()


class TestInsertVideoSegments:
    """Test suite for inserting video segments."""

    @pytest.mark.asyncio
    async def test_insert_video_segments_success(self, adapter):
        """Test inserting video segments successfully."""
        test_df = pd.DataFrame(
            {
                "tenant_id": ["tenant1", "tenant2"],
                "video_id": ["video1", "video2"],
                "segment_start_time": [0.0, 10.0],
                "segment_end_time": [10.0, 20.0],
                "segment_text": ["segment 1", "segment 2"],
                "segment_embedding": [np.array([0.1] * 1536), np.array([0.2] * 1536)],
            }
        )

        with patch.object(adapter, "close"):
            await adapter._insert_video_segments(test_df)

        assert adapter.cursor.execute.call_count == 4
        adapter.conn.commit.assert_called()

    @pytest.mark.asyncio
    async def test_insert_video_segments_with_object_dtype(self, adapter):
        """Test inserting segments with object dtype embeddings."""
        test_df = pd.DataFrame(
            {
                "tenant_id": ["tenant1"],
                "video_id": ["video1"],
                "segment_start_time": [0.0],
                "segment_end_time": [10.0],
                "segment_text": ["segment 1"],
                "segment_embedding": [np.array([[0.1] * 1536], dtype=object)],
            }
        )

        with patch.object(adapter, "close"):
            await adapter._insert_video_segments(test_df)

        adapter.cursor.execute.assert_called()
        adapter.conn.commit.assert_called()


class TestInsertVideos:
    """Test suite for inserting videos."""

    @pytest.mark.asyncio
    async def test_insert_videos_success(self, adapter):
        """Test inserting videos successfully."""
        test_df = pd.DataFrame(
            {
                "video_id": ["video1"],
                "tenant_id": ["tenant1"],
                "title": ["Test Video"],
                "video_url": ["http://example.com"],
                "video_metadata": [{"duration": 100}],
                "video_text": ["Full video text"],
                "text_embedding": [np.array([0.1] * 1536)],
            }
        )

        await adapter._insert_videos(test_df)

        adapter.cursor.execute.assert_called()
        # Check that JSON was dumped
        call_args = adapter.cursor.execute.call_args[0][1]
        assert isinstance(call_args[4], str)


class TestSearchSimilarVectors:
    """Test suite for vector similarity search."""

    @pytest.mark.asyncio
    async def test_search_similar_vectors_cosine(self, adapter):
        """Test searching with cosine similarity."""
        query_embedding = [0.1] * 1536

        # Mock database response
        adapter.cursor.fetchall.return_value = [
            ("video1", 0.0, 10.0, "segment text", 0.1234),
            ("video2", 10.0, 20.0, "another segment", 0.2345),
        ]

        results = await adapter.search_similar_vectors(
            query_embedding, top_k=2, similarity_algorithm="cosine"
        )

        assert len(results) == 2
        assert results[0]["video_id"] == "video1"
        assert results[0]["segment_text"] == "segment text"
        assert results[0]["distance"] == 0.1234

        # Verify correct operator was used
        call_args = adapter.cursor.execute.call_args[0][0]
        assert "<=>" in call_args


class TestClose:
    """Test suite for closing connections."""

    @pytest.mark.asyncio
    async def test_close_connection(self, adapter):
        """Test closing connection and cursor."""
        await adapter.close()

        adapter.cursor.close.assert_called()
        adapter.conn.close.assert_called()

    @pytest.mark.asyncio
    async def test_close_with_error(self, adapter):
        """Test close handles errors."""
        adapter.cursor.close.side_effect = Exception("Close failed")

        with pytest.raises(Exception):
            await adapter.close()
