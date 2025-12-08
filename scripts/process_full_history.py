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

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv

from src.adapters.openai_adapter import AsyncOpenAIApiAdapter
from src.adapters.postgres_database_adapter import AsyncPostgresDatabaseAdapter
from src.application.services.trending_search_service import (
    QueryNormalizationService,
    SemanticClusteringService,
    TrendingSearchConfig,
)

logger = logging.getLogger("process_full_history")
logging.basicConfig(level=logging.INFO)


async def main():
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="When fetching full history, limit to this many most-recent rows",
    )
    args = parser.parse_args()

    config = TrendingSearchConfig()

    # instantiate adapters/services
    db = AsyncPostgresDatabaseAdapter()
    openai_adapter = AsyncOpenAIApiAdapter()
    normalizer = QueryNormalizationService()
    clustering = SemanticClusteringService(config=config)

    try:
        # Fetch all historical queries (None => use max_rows to bound)
        rows = await db.ingest_queries(None, max_rows=args.max_rows)
        if not rows:
            logger.info("No rows found in video_seo_response_history")
            return

        # Normalize queries
        for r in rows:
            r["query"] = await normalizer.normalize(r["original_query"])

        # Deduplicate for embeddings
        unique_queries = list({r["query"] for r in rows})
        logger.info(
            f"Vectorizing {len(unique_queries)} unique queries (from {len(rows)} total)"
        )

        # Get embeddings (this will hit OpenAI)
        embeddings = await openai_adapter.text_embedding(
            text=unique_queries, model=config.EMBEDDING_MODEL
        )

        # Map back to rows
        query_to_embedding = {q: emb for q, emb in zip(unique_queries, embeddings)}
        queries_with_embeddings = []
        for r in rows:
            emb = query_to_embedding.get(r["query"])
            if emb is None:
                # Shouldn't happen, but skip if embedding missing
                continue
            queries_with_embeddings.append(
                {
                    "original_query": r["original_query"],
                    "query": r["query"],
                    "chat_id": r.get("chat_id"),
                    "created_at": r.get("created_at"),
                    "embedding": emb,
                }
            )

        logger.info(f"Running clustering on {len(queries_with_embeddings)} items")

        clusters = await clustering.cluster_queries(queries_with_embeddings)

        embeddings_data = {
            "queries": [q["query"] for q in queries_with_embeddings],
            "embeddings": [q["embedding"] for q in queries_with_embeddings],
        }
        with open(f"embeddings_data.json", "w") as f:
            json.dump(embeddings_data, f)

        queries_data = {
            "queries": [q["query"] for q in queries_with_embeddings],
            "original_queries": [q["original_query"] for q in queries_with_embeddings],
        }
        with open(f"queries_data.json", "w") as f:
            json.dump(queries_data, f)

        logger.info(f"Found {len(clusters)} clusters")
        for cid, indices in clusters.items():
            sample_queries = [queries_with_embeddings[i]["query"] for i in indices[:5]]
            logger.info(
                f"Cluster {cid}: size={len(indices)}, examples={sample_queries}"
            )

        # Optional: save output for offline analysis
        out_path = f"trending_history_clusters.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {str(k): v for k, v in clusters.items()},
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(f"Wrote cluster indices to {out_path}")

    finally:
        try:
            await db.close()
        except Exception:
            pass
