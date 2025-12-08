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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

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

    async def create_trends_table(self) -> None:
        """Create trending_searches table if it doesn't exist with all required columns."""
        try:
            sql = """
                CREATE TABLE IF NOT EXISTS trending_searches (
                    id UUID DEFAULT gen_random_uuid(),
                    representative_query TEXT NOT NULL,
                    representative_query_generated TEXT,
                    trend_score FLOAT NOT NULL,
                    query_count INTEGER NOT NULL,
                    unique_query_count INTEGER NOT NULL,
                    top_queries TEXT,
                    created_at TIMESTAMPTZ NOT NULL,
                    batch_timestamp TIMESTAMPTZ NOT NULL,
                    CONSTRAINT trending_searches_pkey PRIMARY KEY (id)
                );

                CREATE INDEX IF NOT EXISTS idx_trending_batch_timestamp 
                ON trending_searches(batch_timestamp DESC);

                CREATE INDEX IF NOT EXISTS idx_trending_score 
                ON trending_searches(trend_score DESC);

                CREATE INDEX IF NOT EXISTS idx_trending_query
                ON trending_searches(LOWER(representative_query));
            """

            self.cursor.execute(sql)
            self.conn.commit()
            logger.info("Trending searches table ensured with all columns")

        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"Error creating trends table: {e}")
            raise

    async def ingest_queries(
        self, batch_interval_minutes: Optional[int], max_rows: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Ingest queries from the video_seo_response_history table.

        Args:
            batch_interval_minutes (Optional[int]):
                If None, ingest all non-empty historical queries. If an integer, only ingest
                queries created within the last `batch_interval_minutes` minutes (calculated
                using timezone-aware UTC now).
            max_rows (Optional[int]):
                Optional maximum number of rows to return. When provided, a SQL LIMIT is applied
                to constrain the number of returned records.

        Returns:
            List[Dict[str, Any]]:
                A list of dictionaries (ordered by created_at descending) where each dictionary
                contains:
                    - "original_query" (str): the non-empty query text.
                    - "chat_id" (Any): the associated chat identifier.
                    - "created_at" (datetime): the row creation timestamp (timezone-aware UTC).

        Raises:
            Exception:
                Propagates any exception encountered while executing the database query or
                fetching results. The method also logs informational messages on success and
                error details on failure.

        Notes:
            - Rows with NULL or blank (after TRIM) query values are excluded.
            - When batch_interval_minutes is provided, the cutoff is computed as now (UTC)
              minus the given minutes and used as a parameterized query filter.
        """
        try:
            if batch_interval_minutes is None:
                sql = """
                    SELECT 
                        query,
                        chat_id,
                        created_at
                    FROM video_seo_response_history
                    WHERE query IS NOT NULL
                      AND TRIM(query) != ''
                    ORDER BY created_at DESC
                """
                if max_rows is not None:
                    sql = sql.rstrip() + f"\nLIMIT {int(max_rows)}"
                params = ()
            else:
                cutoff_time = datetime.now(timezone.utc) - timedelta(
                    minutes=batch_interval_minutes
                )
                sql = """
                    SELECT 
                        query,
                        chat_id,
                        created_at
                    FROM video_seo_response_history
                    WHERE created_at >= %s
                        AND query IS NOT NULL
                        AND TRIM(query) != ''
                    ORDER BY created_at DESC
                """
                if max_rows is not None:
                    sql = sql.rstrip() + f"\nLIMIT {int(max_rows)}"
                params = (cutoff_time,)

            self.cursor.execute(sql, params)
            rows = self.cursor.fetchall()

            queries = []
            for row in rows:
                queries.append(
                    {"original_query": row[0], "chat_id": row[1], "created_at": row[2]}
                )

            if batch_interval_minutes is None:
                if max_rows is None:
                    logger.info(f"Ingested {len(queries)} total queries from history")
                else:
                    logger.info(
                        f"Ingested {len(queries)} historical queries (limit {max_rows})"
                    )
            else:
                logger.info(
                    f"Ingested {len(queries)} queries from last {batch_interval_minutes} minutes"
                )

            return queries

        except Exception as e:
            logger.error(f"Error ingesting queries: {e}")
            raise

    async def persist_trends(
        self, ranked_trends: List[Dict[str, Any]], batch_timestamp: datetime
    ) -> None:
        """Persist trending search records into `trending_searches`."""
        try:
            await self.create_trends_table()

            sql = """
                INSERT INTO trending_searches (
                    representative_query,
                    representative_query_generated,
                    trend_score,
                    query_count,
                    unique_query_count,
                    top_queries,
                    created_at,
                    batch_timestamp
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """

            for trend in ranked_trends:
                self.cursor.execute(
                    sql,
                    (
                        trend.get("representative_query"),
                        trend.get("representative_query_generated"),
                        float(trend.get("trend_score", 0)),
                        int(trend.get("query_count", 0)),
                        int(trend.get("unique_query_count", 0)),
                        json.dumps(trend.get("top_queries")),
                        trend.get("created_at"),
                        batch_timestamp,
                    ),
                )

            self.conn.commit()
            logger.info(f"Successfully persisted {len(ranked_trends)} trends")

        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"Error persisting trends: {e}")
            raise

    async def get_current_trends(
        self, limit: int = 20, min_score: float = 0.0
    ) -> Dict[str, Any]:
        """Retrieve current trends for the most recent batch_timestamp and format results."""
        try:
            sql = """
                SELECT 
                    representative_query,
                    representative_query_generated,
                    trend_score,
                    query_count,
                    unique_query_count,
                    top_queries,
                    created_at,
                    batch_timestamp
                FROM trending_searches
                WHERE batch_timestamp = (
                    SELECT MAX(batch_timestamp) FROM trending_searches
                )
                AND trend_score >= %s
                ORDER BY trend_score DESC
                LIMIT %s
            """

            self.cursor.execute(sql, (min_score, limit))
            rows = self.cursor.fetchall()

            trends = []
            for row in rows:
                trends.append(
                    {
                        "query": row[0],
                        "representative_query_generated": row[1],
                        "trend_score": round(float(row[2]), 4),
                        "query_count": row[3],
                        "unique_query_count": row[4],
                        "top_queries": row[5],
                        "created_at": row[6],
                        "batch_timestamp": row[7],
                    }
                )

            return {"status": "success", "trends": trends, "count": len(trends)}

        except Exception as e:
            logger.error(f"Error retrieving current trends: {e}")
            return {"status": "error", "trends": [], "count": 0, "error": str(e)}

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

    async def insert_into_session_table(
        self,
        chat_id: UUID,
        response: List[Dict[str, Any]],
        query: str,
        created_at: datetime,
        temporary_id: Optional[str] = None,
    ) -> None:
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
                    query_embedding = (
                        query_embedding[0].tolist()
                        if len(query_embedding) > 0
                        else query_embedding.tolist()
                    )
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

    async def create_materialized_video_stat_table(self) -> None:
        """Create a materialized view 'video_stats_view' that aggregates like, view, share, and post counts per video and commits it to the PostgreSQL database.
        Args:
            self: Instance of the adapter providing an active DB connection and cursor.
        Returns:
            None
        """

        try:
            video_stat_query = """
                            create materialized view if not exists video_stats_view
                            as
                            select v.id as video_id, count(vl."Id") as like_count, count(vv."Id") as view_count,
                            count(vs."Id") as share_count, count(vp."Id") as post_count
                            -- select *
                            from videos v
                            left join "VideoLikes" vl on v.id = vl."VideoId" 
                            left join "VideoViews" vv on v.id = vv."VideoId"
                            left join "VideoShares" vs on v.id = vs."VideoId"
                            left join "VideoPosts" vp on vp."VideoShareId" = vs."Id"
                            where v.id not in (
                                select vr."VideoId"
                                from "Reports" vr
                                where vr."IsResolved" is false
                            )
                            group by v.id;
                        """

            logger.info(f"creating table video_seo_response_history ")
            self.cursor.execute(video_stat_query)
            self.conn.commit()
        except Exception as e:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"Failed to create table : {e}")
            raise

    async def search_popular_videos(self, limit: Optional[int] = 15) -> List:
        """
        Return a list of popular video IDs ordered by a computed popularity score.
        Args:
            limit (Optional[int]): Maximum number of popular videos to return. If a negative value is provided, the default of 15 is used.
        Returns:
            List: A list of video_id values ordered by descending popularity score (computed as view_count * 1 + like_count * 10 + share_count * 20).
        """

        try:
            if limit < 0:
                limit = 15

            popular_videos_search_query = f"""
            SELECT 
            video_id, 
            view_count, 
            like_count, 
            share_count, 
            (view_count * 1 + like_count * 10 + share_count * 20) AS popularity_score
            FROM video_stats_view
            ORDER BY popularity_score DESC
            LIMIT {limit};
            """
            logger.info("Searching popular videos")

            self.cursor.execute(query=popular_videos_search_query)
            rows = self.cursor.fetchall()

            results = []
            for row in rows:
                results.append(row[0])
            print("the popular videos are:", results)
            return results
        except errors.UndefinedTable as e:
            logger.error(f"Table not found for searching: {e}")
            raise

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            raise

    async def refresh_materialized_view_tables(self):
        """Refresh the 'video_stats_view' materialized view in the connected PostgreSQL database.
        Args:
            self: The adapter instance containing an active DB connection and cursor used to execute the refresh.
        Returns:
            None
        """

        try:
            refresh_query = """ REFRESH MATERIALIZED VIEW video_stats_view;"""
            self.cursor.execute(refresh_query)
            self.conn.commit()
        except:
            try:
                self.conn.rollback()
            except:
                pass
            logger.error(f"Failed to refresh materialized view")
            raise

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
