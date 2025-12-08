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
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
import json

from src.application.services.trending_search_service import (
    QueryNormalizationService,
    SemanticClusteringService,
    TrendScoringService,
    RepresentativeQueryService,
    TrendingSearchConfig,
)
from src.ports.output import AsyncOpenAIAPIPort, PostgresDatabasePort

logger = logging.getLogger(__name__)

class TrendingSearchAdapter:
    """
    Pipeline adapter that orchestrates the trending search workflow.
    
    Responsibilities:
    - Coordinates between services and external systems
    - Manages data flow through the pipeline
    - Handles I/O operations (database, API calls)
    - Implements the complete batch processing workflow
    """

    def __init__(
        self,
        database_port: PostgresDatabasePort,
        openai_client_port: AsyncOpenAIAPIPort,
        config: TrendingSearchConfig = None
    ):
        """
        Initialize the pipeline adapter.
        
        Args:
            database_port: Database output port for data access
            openai_client_port: OpenAI API output port for embeddings
            config: Optional configuration override
        """
        self.database_port = database_port
        self.openai_client_port = openai_client_port
        self.config = config or TrendingSearchConfig()
        
        # Initialize services
        self.normalization_service = QueryNormalizationService()
        self.clustering_service = SemanticClusteringService(config=self.config)
        self.scoring_service = TrendScoringService(config=self.config)
        self.representative_service = RepresentativeQueryService()

    async def run_batch_pipeline(self) -> Dict[str, Any]:
        """
        Execute the complete trending search pipeline.
        
        Pipeline steps:
        1. Ingest recent queries from database
        2. Normalize query text
        3. Vectorize queries using OpenAI
        4. Cluster queries semantically
        5. Score and rank clusters
        6. Persist results to database
        
        Returns:
            Dictionary with processing results:
                - status: "success" or "error"
                - trends_identified: Number of trends found
                - total_queries_processed: Number of queries analyzed
                - error: Error message if any
        """
        try:
            logger.info("=" * 60)
            logger.info("Starting trending search batch pipeline")
            logger.info(f"Timestamp: {datetime.now(timezone.utc)}")

            raw_queries = await self.database_port.ingest_queries(
                batch_interval_minutes=self.config.BATCH_INTERVAL_MINUTES,
                max_rows=40,
            )

            if not raw_queries or len(raw_queries) < self.config.MIN_CLUSTER_SIZE:
                logger.info(
                    f"Insufficient queries ({len(raw_queries) if raw_queries else 0}) "
                    f"for trending analysis"
                )
                return {
                    "status": "success",
                    "trends_identified": 0,
                    "total_queries_processed": len(raw_queries) if raw_queries else 0,
                    "message": "Insufficient data for clustering"
                }
            
            normalized_queries = await self._normalize_queries(raw_queries)

            queries_with_embeddings = await self._vectorize_queries(normalized_queries)

            clusters = await self.clustering_service.cluster_queries(queries_with_embeddings)

            if not clusters:
                logger.info("No clusters identified (all queries marked as noise)")
                return {
                    "status": "success",
                    "trends_identified": 0,
                    "total_queries_processed": len(raw_queries),
                    "message": "No semantic clusters found"
                }
            
            ranked_trends = await self.scoring_service.score_and_rank_clusters(
                clusters, 
                queries_with_embeddings
            )

            # Optionally generate an LLM-crafted short representative phrase for each trend
            for trend in ranked_trends:
                top_qs = trend.get("top_queries")
                if isinstance(top_qs, str):
                    try:
                        parsed = json.loads(top_qs)
                        if isinstance(parsed, list):
                            top_qs = parsed
                        else:
                            # not a list after parsing; fallback to using representative_query
                            top_qs = [trend.get("representative_query")]
                    except Exception:
                        # fallback: wrap existing string into a single-item list
                        top_qs = [top_qs]

                if not isinstance(top_qs, list):
                    top_qs = [str(top_qs)] if top_qs is not None else []

                try:
                    if len(top_qs) > 0:
                        rep_obj = await self.representative_service.craft_representative_query(
                            self.openai_client_port, [str(q) for q in top_qs], max_words=4
                        )
                        if rep_obj and hasattr(rep_obj, 'query'):
                            trend["representative_query_generated"] = rep_obj.query
                except Exception as e:
                    logger.warning(f"Failed to generate representative phrase for trend: {e}")

            # Persist trends (adapter is responsible for DB schema and inserts)
            batch_timestamp = datetime.now(timezone.utc)
            await self.database_port.persist_trends(ranked_trends, batch_timestamp)

            logger.info(f"Successfully processed {len(ranked_trends)} trending topics")
            logger.info("=" * 60)
            
            return {
                "status": "success",
                "trends_identified": len(ranked_trends),
                "total_queries_processed": len(raw_queries)
            }
            
        except Exception as e:
            logger.error(f"Error in trending pipeline: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "trends_identified": 0,
                "total_queries_processed": 0
            }
        
    async def get_current_trends(
        self,
        limit: int = 20,
        min_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Fetch formatted current trends via the database adapter."""
        try:
            resp = await self.database_port.get_current_trends(limit=limit, min_score=min_score)

            # Build response matching TrendingSearchResponseModel
            response_out: Dict[str, Any] = {"status": "error", "trending_searches": [], "error": None}

            if resp.get("status") != "success":
                response_out["error"] = resp.get("error")
                return response_out

            trends = resp.get("trends", [])
            decorated: List[str] = []

            for trend in trends:
                # top_queries may be JSON (list) or string
                top_qs = trend.get("top_queries")
                if isinstance(top_qs, str):
                    try:
                        parsed = json.loads(top_qs)
                        if isinstance(parsed, list):
                            top_qs = parsed
                    except Exception:
                        top_qs = [top_qs]

                if not isinstance(top_qs, list):
                    top_qs = [str(top_qs)] if top_qs is not None else []

                # Generate representative phrase via service; fallback to DB representative
                rep_phrase = ""
                try:
                    if len(top_qs) > 0:
                        rep_obj = await self.representative_service.craft_representative_query(
                            self.openai_client_port, [str(q) for q in top_qs], max_words=4
                        )
                        if rep_obj and hasattr(rep_obj, 'query'):
                            rep_phrase = rep_obj.query
                except Exception as e:
                    logger.warning(f"Representative phrase generation failed: {e}")

                if not rep_phrase:
                    # Use persisted representative phrase if available, otherwise fall back to representative_query
                    rep_phrase = trend.get("representative_query_generated") or trend.get("query") or trend.get("representative_query") or ""
                
                if isinstance(rep_phrase, str):
                    rep_phrase = rep_phrase.capitalize()

                decorated.append(rep_phrase)

            response_out["status"] = "success"
            response_out["trending_searches"] = decorated
            return response_out
        except Exception as e:
            logger.error(f"Error retrieving current trends: {e}")
            return {"status": "error", "trending_searches": [], "error": str(e)}

    

    async def _normalize_queries(
        self, 
        raw_queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Normalize all queries using the normalization service.
        
        Args:
            raw_queries: List of raw query dictionaries
            
        Returns:
            List of queries with normalized text added
        """
        for query_data in raw_queries:
            normalized = await self.normalization_service.normalize(
                query_data["original_query"]
            )
            query_data["query"] = normalized
        
        return raw_queries
    
    async def _vectorize_queries(
        self, 
        queries_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert all queries to embeddings using OpenAI API.
        
        Implements deduplication to minimize API calls.
        
        Args:
            queries_data: List of query dictionaries with normalized text
            
        Returns:
            List of query dicts with added 'embedding' field
        """
        try:
            # Extract unique queries to avoid duplicate embedding calls
            unique_queries = list(set(q["query"] for q in queries_data))
            
            logger.info(
                f"Vectorizing {len(unique_queries)} unique queries "
                f"(from {len(queries_data)} total)"
            )
            
            # Batch embed all unique queries
            embeddings = await self.openai_client_port.text_embedding(
                text=unique_queries,
                model=self.config.EMBEDDING_MODEL
            )
            
            # Create embedding lookup
            query_to_embedding = {
                query: embedding 
                for query, embedding in zip(unique_queries, embeddings)
            }
            
            # Attach embeddings to original queries
            for query_data in queries_data:
                query_data["embedding"] = query_to_embedding[query_data["query"]]
            
            logger.info(f"Successfully vectorized {len(queries_data)} queries")
            return queries_data
            
        except Exception as e:
            logger.error(f"Error vectorizing queries: {e}")
            raise

    

    