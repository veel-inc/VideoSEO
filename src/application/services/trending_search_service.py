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
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from typing import Optional
from src.ports.output.openai_api_port import AsyncOpenAIAPIPort
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances
from collections import Counter
import json

from src.application.prompts import SanitizedQueryPrompt

from src.domain.models.trending_search_models import RepresentativeQueryModel

logger = logging.getLogger(__name__)


class TrendingSearchConfig:
    """Configuration for trending search processing."""
    
    BATCH_INTERVAL_MINUTES = None
    MIN_CLUSTER_SIZE = 3
    DBSCAN_EPS = 0.418182
    DBSCAN_MIN_SAMPLES = 2
    TOP_N_TRENDS = 20
    EMBEDDING_MODEL = "text-embedding-3-small"
    VOLUME_WEIGHT = 0.6
    RECENCY_WEIGHT = 0.4
    RECENCY_DECAY_MINUTES = 5

class QueryNormalizationService:
    """Service for normalizing and cleaning query text."""
    
    @staticmethod
    async def normalize(query: str) -> str:
        """
        Normalize query text for better clustering.
        
        Args:
            query: Raw query string
            
        Returns:
            Normalized query string
        """
        # Convert to lowercase and strip whitespace
        query = query.lower().strip()
        
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        # Remove trailing punctuation
        query = query.rstrip('?!.,')
        
        return query
    
class SemanticClusteringService:
    """
    Service for clustering queries based on semantic similarity.
    Uses DBSCAN algorithm with cosine distance.
    """
    
    def __init__(self, config: TrendingSearchConfig = None):
        """
        Initialize clustering service.
        
        Args:
            config: Optional configuration override
        """
        self.config = config or TrendingSearchConfig()

    async def cluster_queries(
        self, 
        queries_with_embeddings: List[Dict[str, Any]]
    ) -> Dict[int, List[int]]:
        """
        Apply DBSCAN clustering to group semantically similar queries.
        
        Args:
            queries_with_embeddings: List of query dicts with embeddings
            
        Returns:
            Dictionary mapping cluster_id to list of query indices
        """
        try:
            # Extract embeddings matrix
            embeddings_matrix = np.array([
                q["embedding"] for q in queries_with_embeddings
            ])
            
            logger.info(f"Clustering {len(embeddings_matrix)} query vectors")
            logger.info(
                f"DBSCAN params: eps={self.config.DBSCAN_EPS}, "
                f"min_samples={self.config.DBSCAN_MIN_SAMPLES}"
            )

            distance_matrix = cosine_distances(embeddings_matrix)

            # Apply DBSCAN
            dbscan = DBSCAN(
                eps=self.config.DBSCAN_EPS,
                min_samples=self.config.DBSCAN_MIN_SAMPLES,
                metric='precomputed'
            )

            cluster_labels = dbscan.fit_predict(distance_matrix)

            clusters = {}
            noise_count = 0
            
            for idx, label in enumerate(cluster_labels):
                if label == -1:
                    noise_count += 1
                else:
                    if label not in clusters:
                        clusters[label] = []
                    clusters[label].append(idx)

            logger.info(
                f"Identified {len(clusters)} clusters, "
                f"{noise_count} noise points filtered"
            )
            
            # Log cluster size distribution
            if clusters:
                cluster_sizes = [len(indices) for indices in clusters.values()]
                logger.info(
                    f"Cluster sizes: min={min(cluster_sizes)}, "
                    f"max={max(cluster_sizes)}, avg={np.mean(cluster_sizes):.1f}"
                )
            
            return clusters
            
        except Exception as e:
            logger.error(f"Error clustering queries: {e}")
            raise

class TrendScoringService:
    """
    Service for scoring and ranking trend clusters.
    Combines volume and recency metrics.
    """
    
    def __init__(self, config: TrendingSearchConfig = None):
        """
        Initialize scoring service.
        
        Args:
            config: Optional configuration override
        """
        self.config = config or TrendingSearchConfig()


    async def score_and_rank_clusters(
        self,
        clusters: Dict[int, List[int]],
        queries_with_embeddings: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Score clusters based on volume and recency, then rank them.
        
        Args:
            clusters: Dictionary mapping cluster_id to query indices
            queries_with_embeddings: Original queries with embeddings
            
        Returns:
            Sorted list of trend dictionaries with scores
        """
        try:
            trends = []

            for cluster_id, query_indices in clusters.items():
                if len(query_indices) < self.config.MIN_CLUSTER_SIZE:
                    continue

                # Extract cluster queries
                cluster_queries = [
                    queries_with_embeddings[idx] for idx in query_indices
                ]

                # Calculate trend score
                trend_score = await self._calculate_trend_score(cluster_queries)
                
                # Find representative query (centroid)
                centroid_query = await self._find_centroid_query(
                    cluster_queries, query_indices
                )

                # Get query frequency distribution
                query_texts = [q["query"] for q in cluster_queries]
                query_counts = Counter(query_texts)

                trends.append({
                    "cluster_id": cluster_id,
                    "representative_query": centroid_query,
                    "trend_score": trend_score,
                    "query_count": len(cluster_queries),
                    "unique_query_count": len(query_counts),
                    "top_queries": str(query_counts.most_common(5)),
                    "created_at": datetime.now(timezone.utc)
                })

            # Sort by trend score (descending)
            ranked_trends = sorted(
                trends, 
                key=lambda x: x["trend_score"], 
                reverse=True
            )[:self.config.TOP_N_TRENDS]
            
            logger.info(f"Ranked top {len(ranked_trends)} trends")
            
            return ranked_trends
            
        except Exception as e:
            logger.error(f"Error scoring and ranking clusters: {e}")
            raise

    async def _calculate_trend_score(
        self, 
        cluster_queries: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate trend score based on volume and recency.
        
        Score = (volume * VOLUME_WEIGHT) + (recency_score * RECENCY_WEIGHT)
        
        Args:
            cluster_queries: List of queries in the cluster
            
        Returns:
            Trend score (higher = more trending)
        """
        volume_score = len(cluster_queries)

        # Recency boost: recent queries weighted more
        now = datetime.now(timezone.utc)
        recency_weights = []
        
        for query in cluster_queries:
            time_diff = (now - query["created_at"]).total_seconds() / 60
            # Exponential decay
            recency_weight = np.exp(-time_diff / self.config.RECENCY_DECAY_MINUTES)
            recency_weights.append(recency_weight)
        
        recency_score = sum(recency_weights)
        
        # Combined score
        trend_score = (
            volume_score * self.config.VOLUME_WEIGHT + 
            recency_score * self.config.RECENCY_WEIGHT
        )
        
        return round(trend_score, 4)
    
    async def _find_centroid_query(
        self,
        cluster_queries: List[Dict[str, Any]],
        query_indices: List[int]
    ) -> str:
        """
        Find the most representative query (closest to cluster centroid).
        
        Args:
            cluster_queries: Queries in the cluster
            query_indices: Original indices of queries
            
        Returns:
            Representative query string
        """
        # Compute cluster centroid
        embeddings = np.array([q["embedding"] for q in cluster_queries])
        centroid = np.mean(embeddings, axis=0)
        
        # Find query closest to centroid
        distances = cosine_distances(embeddings, centroid.reshape(1, -1))
        closest_idx = np.argmin(distances)
        
        return cluster_queries[closest_idx]["query"]


class RepresentativeQueryService:
    """
    Service responsible for crafting a short, grammatically-coherent representative
    query phrase for a cluster by calling the OpenAI response port.
    """

    @staticmethod
    async def craft_representative_query(
        openai_port: AsyncOpenAIAPIPort,
        top_queries: List[str],
        max_words: int = 4,
        model: Optional[str] = "gpt-4o",
        temperature: float = 0.3,
    ) -> RepresentativeQueryModel:
        """
        Use the provided OpenAI port to craft a concise representative phrase.

        Args:
            openai_port: An implementation of AsyncOpenAIAPIPort
            top_queries: List of top query strings to summarize
            max_words: Maximum words to include in the returned phrase
            model: Optional model override
            temperature: Sampling temperature

        Returns:
            A short representative phrase (may be empty string on error)
        """
        if not top_queries:
            return RepresentativeQueryModel(query="")

        instructions = SanitizedQueryPrompt().SANITIZED_QUERY_PROMPT_TEMPLATE.format(
            max_words=max_words
        )

        user_input = "\n".join(top_queries)

        openai_response = await openai_port.structured_response(
            user_input=user_input,
            instructions=instructions,
            model=model,
            schema_model=RepresentativeQueryModel,
            temperature=temperature,
            tools=None,
        )

        try:
            response = json.loads(openai_response.output[0].arguments)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse OpenAI response: {e}")
            raise

        return RepresentativeQueryModel.model_validate(response)

