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

import json
import logging
import os
from uuid import UUID
from pathlib import Path
from typing import Any, Dict, List, Union, Optional
from datetime import datetime

import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2 import Error, OperationalError, errors

from src.ports.output import PostgresDatabasePort

load_dotenv()

logger = logging.getLogger(__name__)


class AsyncPostgresDatabaseAdapter(PostgresDatabasePort):
    def __init__(self, conn=None):
        self.dbname = os.getenv("DATABASE_NAME", os.environ.get("DATABASE_NAME", None))
        self.host = os.getenv("DATABASE_HOST", os.environ.get("DATABASE_HOST", None))
        self.port = os.getenv("DATABASE_PORT", os.environ.get("DATABASE_PORT", None))
        self.user = os.getenv("DATABASE_USER", os.environ.get("DATABASE_USER", None))
        self.password = os.getenv(
            "DATABASE_PASSWORD", os.environ.get("DATABASE_PASSWORD", None)
        )

        if (
            not self.dbname
            or not self.host
            or not self.port
            or not self.user
            or not self.password
        ):
            logger.error("Database credentials are not set in environment variables")
            raise ValueError("Database Credentials not set in environment variables")

        try:
            self.conn = conn or psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
            )
            self.cursor = self.conn.cursor()
            logger.info("Connected to Postgres database")
        except OperationalError as e:
            logger.error(f"Could not connect to PostgreSQL: {e}")
            raise RuntimeError("Database connection failed") from e

        except Error as e:
            logger.error(f"Some other database error occurred: {e}")
            raise

        self._setup_extensions(extension_name=["vector", "uuid-ossp"])

    def _setup_extensions(self, extension_name: Union[str, List[str]]) -> None:
        """
        Ensure that one or more PostgreSQL extensions are installed for the current
        database connection by executing "CREATE EXTENSION IF NOT EXISTS" for each
        provided extension name.

        Args:
            extension_name (Union[str, List[str]]): A single extension name as a string
                or a list of extension names to be created/ensured.

        Returns:
            None: This method performs side effects on the database (executing SQL
            statements). On failure, the connection is rolled back and the original
            exception is re-raised.
        """
        try:
            if isinstance(extension_name, str):
                self.cursor.execute(
                    f'CREATE EXTENSION IF NOT EXISTS "{extension_name}";'
                )
            else:
                for extension in extension_name:
                    self.cursor.execute(
                        f'CREATE EXTENSION IF NOT EXISTS "{extension}";'
                    )

        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"Failed to setup extensions: {e}")
            raise

    async def create_table(self, table_name: str) -> None:
        """Create the specified database table if it does not already exist.
        This asynchronous method constructs and executes a CREATE TABLE statement for
        one of the supported table schemas and applies the change to the connected
        Postgres database.
        Args:
            table_name (str): The name of the table to create. Supported values:
                - "videos": creates a videos table with fields for id, tenant_id,
                  title, video_url, video_metadata, video_text and a 1536-dim vector
                  column for embeddings.
                - "video_segments": creates a video_segments table with fields for id,
                  tenant_id, video_id, segment_start_time, segment_end_time,
                  segment_text and a 1536-dim vector column for embeddings.
        Returns:
            None
        Raises:
            ValueError: If table_name is not one of the supported table names.
            Exception: If SQL execution fails; the method rolls back the transaction
                       and re-raises the original exception.
        """

        try:
            if table_name == "videos":
                table_query = f"""
                        CREATE TABLE IF NOT EXISTS {table_name}(
                        id UUID DEFAULT uuidv7(),
                        tenant_id TEXT,
                        title TEXT,
                        video_url TEXT,
                        video_metadata JSONB,
                        video_text TEXT,
                        text_embedding VECTOR(1536),
                        CONSTRAINT videos_pkey PRIMARY KEY (id)
                        );
                """
                logger.info(f"Creating table: {table_name}")

            elif table_name == "video_segments":
                table_query = f"""
                                CREATE TABLE IF NOT EXISTS {table_name}(
                                id UUID DEFAULT uuidv7(),
                                tenant_id TEXT,
                                video_id uuid, 
                                segment_start_time float,
                                segment_end_time float,
                                segment_text TEXT,
                                segment_embedding VECTOR(1536),
                                CONSTRAINT video_segments_pkey PRIMARY KEY (id)
                                );

                                """
                logger.info(f"Creating table: {table_name}")

            else:
                raise ValueError(f"Unknown table name: {table_name}")

            self.cursor.execute(table_query)
            self.conn.commit()
            logger.info(f"Table {table_name} created successfully")
        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"Failed to create table {table_name}: {e}")
            raise
        finally:
            await self.conn.close()

    async def create_session_table(
        self,
    ) -> None:
        """Create the video_seo_response_history table if it does not already exist.
        Description:
            Executes a CREATE TABLE IF NOT EXISTS statement against the adapter's
            PostgreSQL connection to ensure the `video_seo_response_history` table is
            present. The intended table contains an `id` UUID column with a default
            generator, a `response` JSONB column, and a primary key constraint on `id`.
            The method logs the creation attempt, commits the transaction on success,
            and attempts to rollback on failure before re-raising the exception.
        Args:
            self: Adapter instance providing a PostgreSQL connection and cursor
                (for example, attributes `self.conn` and `self.cursor`). These are used
                to execute the DDL statement and to commit/rollback the transaction.
        Returns:
            None
        Raises:
            Exception: Any exception raised while executing the DDL or committing the
                transaction is re-raised after an attempted rollback. The exception
                contains details about the failure.
        """

        try:
            table_query = """
                            CREATE TABLE IF NOT EXISTS video_seo_response_history(
                            id uuid DEFAULT uuidv7(),
                            chat_id uuid,
                            temporary_id TEXT DEFAULT null,
                            response JSONB,
                            query Text,
                            created_at TIMESTAMPTZ DEFAULT NOW(),
                            CONSTRAINT video_seo_response_history_pkey PRIMARY KEY (id)
                            );
                        """

            logger.info(f"creating table video_seo_response_history ")
            self.cursor.execute(table_query)
            self.conn.commit()
        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"Failed to create table : {e}")
            raise

    async def insert_into_session_table(self,chat_id:UUID, response: List[Dict[str, Any]],query:str, created_at:datetime, temporary_id:Optional[str]=None) -> None:
        """Insert a list of response objects into the video_seo_response_history database table.
        Args:
            chat_id (UUID): unique user id
            response (List[Dict[str, Any]]): A list of dictionaries representing responses to be
                serialized to JSON
            query (str): query searched.
            created_at (datetime): timestamp when the response was inserted
            temporary_id (Optional[str]): temporary id of the unauthorized user
        Returns:
            None
        Raises:
            Exception: If the database insert or commit fails; the method will attempt a rollback
            and close the connection before re-raising the exception
        """
        try:
            logger.info("Inserting responses into database")

            await self.create_session_table()

            sql = """
            INSERT INTO video_seo_response_history (
                chat_id, temporary_id, response, query, created_at
            )
                VALUES (%s, %s, %s, %s, %s)
            """

            self.cursor.execute(
                sql,
                (
                    chat_id,
                    temporary_id,
                    json.dumps(response),
                    query,
                    created_at,
                ),
            )

            self.conn.commit()
            logger.info(f"Inserted response with id {chat_id}")
        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"Unable to insert data into table:{e}")
            raise
        finally:
            await self.close()

    async def bulk_insert_from_parquet(self, parquet_file_path: str | Path) -> None:
        """Bulk insert rows from a Parquet file into the database.
        Args:
            parquet_file_path (str | Path): Path to the Parquet file to read (string or pathlib.Path).
        Returns:
            None: Performs database insertion as a side effect and does not return a value.
        """
        try:
            df = pd.read_parquet(parquet_file_path)
            logger.info(f"the filepath is: {parquet_file_path}")
            file_name = Path(parquet_file_path).name
            logger.info(f"Processing file: {file_name}")
            logger.info(f"Dataframe shape: {df.shape}")

            if file_name.split("_")[0] == "segment":
                await self._insert_video_segments(df=df)
            else:
                await self._insert_videos(df)

            logger.info(f"Successfully inserted data from {parquet_file_path}")

        except Exception as e:
            logger.error(f"An unexpected error occured while inserting data {e}")
            raise

    async def _insert_video_segments(self, df: pd.DataFrame) -> None:
        """Insert video segment records from a DataFrame into the video_segments table.
        Args:
            df (pd.DataFrame): DataFrame containing the following columns for each row:
                - tenant_id: Identifier for the tenant.
                - video_id: Identifier for the video.
                - segment_start_time: Segment start timestamp/offset.
                - segment_end_time: Segment end timestamp/offset.
                - segment_text: Text content of the segment.
                - segment_embedding: Embedding for the segment (list or numpy array); will be converted to a list
                  before insertion.
        Returns:
            None: Commits inserted rows to the database on success. On failure, attempts to roll back the transaction
            and re-raises the exception; the method also ensures the database connection is closed.
        """

        try:
            logger.info("inserting into video segments table")
            print("")

            sql = """
                    INSERT INTO video_segments(
                    tenant_id, video_id, segment_start_time, segment_end_time, segment_text, segment_embedding 
                    )
                    VALUES (%s, %s, %s, %s,%s, %s::vector)
                """

            for _, row in df.iterrows():
                print(type(row["segment_embedding"]))
                print(row["segment_embedding"])
                emb = row["segment_embedding"]
                if isinstance(emb, np.ndarray):
                    if emb.dtype == object:
                        emb = emb[0].tolist() if len(emb) > 0 else emb.tolist()
                    else:
                        emb = emb.tolist()

                self.cursor.execute(
                    sql,
                    (
                        row.get("tenant_id"),
                        row["video_id"],
                        row["segment_start_time"],
                        row["segment_end_time"],
                        row["segment_text"],
                        emb,
                    ),
                )

            self.conn.commit()
            logger.info(f"Inserted {len(df)} video segments")
        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(
                f"An unexpected error occured during inserting video segments: {e}"
            )
            raise
        finally:
            await self.close()

    async def _insert_videos(self, df: pd.DataFrame) -> None:
        """Insert rows from the provided DataFrame into the "videos" PostgreSQL table.
        Args:
            df (pd.DataFrame): DataFrame containing video records to insert. Expected columns:
                - video_id: unique identifier for the video
                - tenant_id: tenant identifier
                - title: video title
                - video_url: URL of the video
                - video_metadata: dict-like object (will be JSON-dumped before insertion)
                - video_text: textual content of the video
                - text_embedding: list or numpy.ndarray convertible to a Python list (stored as a Postgres vector)
        Returns:
            None: Commits the transaction on success; may raise Exceptions on failure.

        """
        try:
            logger.info("Inserting into video table")
            sql = """
                    INSERT INTO videos(
                    id,tenant_id, title, video_url, video_metadata, video_text, text_embedding
                    )
                    VALUES (%s,%s, %s, %s, %s, %s, %s::vector)
                    """
            for _, row in df.iterrows():
                emb = row["text_embedding"]
                if isinstance(emb, np.ndarray):
                    if emb.dtype == object:
                        emb = emb[0].tolist() if len(emb) > 0 else emb.tolist()
                    else:
                        emb = emb.tolist()

                self.cursor.execute(
                    sql,
                    (
                        row["video_id"],
                        row["tenant_id"],
                        row["title"],
                        row["video_url"],
                        json.dumps(row["video_metadata"]),
                        row["video_text"],
                        emb,
                    ),
                )

            self.conn.commit()
            logger.info(f"Inserted parquet file {len(df)} into table videos")
        except Exception as e:
            try:
                self.conn.roll()
            except:
                pass
            logger.error(f"An unexpected error occured during :{e}")
            raise
        finally:
            await self.close()

    async def search_similar_vectors(
        self, query_embedding: list[float], top_k=250, similarity_algorithm="cosine"
    ) -> List[Dict[str, Any]]:
        """Search for the top-K most similar video segment embeddings to a given query embedding using PostgreSQL (pgvector).
        Args:
            query_embedding (list[float] | numpy.ndarray): The embedding vector to search against the stored segment embeddings.
            top_k (int, optional): The maximum number of similar results to return. Defaults to 10.
            similarity_algorithm (str, optional): Similarity metric to use; "cosine" selects the cosine operator (<=>), otherwise a distance operator (<->) is used. Defaults to "cosine".
        Returns:
            List[Dict[str, Any]]: A list of result dictionaries ordered by increasing distance (more similar first). Each dict contains:
                - "video_id": Identifier of the video associated with the segment.
                - "segment_start_time": Segment start time (numeric).
                - "segment_end_time": Segment end time (numeric).
                - "segment_text": Transcript or text of the segment.
                - "distance": Numeric distance score (float), rounded to 4 decimal places.
        """

        try:
            if isinstance(query_embedding, np.ndarray):
                if query_embedding.dtype == object:
                    query_embedding = query_embedding[0].tolist() if len(query_embedding) > 0 else query_embedding.tolist()
                else:
                    query_embedding = query_embedding.tolist()

            operator = "<=>" if similarity_algorithm == "cosine" else "<->"

            sql = f"""
                    SELECT 
                    video_id,
                    segment_start_time,
                    segment_end_time,
                    segment_text,
                    segment_embedding {operator} %s::vector AS distance
                    FROM video_segments
                    ORDER BY segment_embedding <=> %s::vector ASC
                    LIMIT %s
            """
            self.cursor.execute(sql, (query_embedding, query_embedding, top_k))
            rows = self.cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "video_id": row[0],
                        "segment_start_time": row[1],
                        "segment_end_time": row[2],
                        "segment_text": row[3],
                        "distance": round(float(row[4]), 4),
                    }
                )
            return results

        except errors.UndefinedTable as e:
            logger.error(f"Table not found for searching: {e}")
            raise

        except Exception as e:
            logger.error(f"An unexpected error occured: {e}")
            raise

    async def implement_ivfflat_indexing(self):
        """Create and train an ivfflat index on the video_segments.segment_embedding column using vector_cosine_ops.
        Args:
            self: Instance containing 'cursor' (database cursor), 'conn' (database connection) and an async 'close' method; this method executes SQL to create the index, commits on success, and attempts rollback on error.
        Returns:
            None
        """

        try:
            create_index_query = """
                        CREATE INDEX IF NOT EXISTS idx_video_segments 
                        ON video_segments 
                        USING ivfflat (segment_embedding vector_cosine_ops) 
                        WITH (lists = 100);
                    """
            self.cursor.execute(query=create_index_query)

            # train_index_query = """
            #                 SELECT ivfflat_train('idx_video_segments');
            #             """
            # self.cursor.execute(query=train_index_query)

            self.conn.commit()
            logger.info("Indexing created and trained successfully")
        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"An unexpected error occured: {e}")
            raise
        finally:
            await self.close()

    async def close(self) -> None:
        """Close the database connection and associated cursor, releasing resources.
        Args:
            None
        Returns:
            None: This coroutine returns nothing; it completes when the cursor and connection have been closed (may raise an exception if closing fails).
        """

        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()

            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
            raise
