import logging
from collections import defaultdict
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from src.domain.models import (
    SegmentWithVideoIDModel,
    VideoSegmentModel,
    VideoSEOResponseModel,
)
from src.ports.input import VideoSEOQueryPort
from src.ports.output import AsyncOpenAIAPIPort, PostgresDatabasePort

logger = logging.getLogger(__name__)


def group_segments_by_video_id(raw_segments: list):
    """
    Group raw segment dictionaries by their video_id and convert them into SegmentWithVideoIDModel dictionaries.
    Args:
        raw_segments (list): List of dictionaries representing segments. Each dictionary is expected to include the keys:
            - "video_id" (str | int): Identifier of the video the segment belongs to.
            - "segment_text" (str): Text content of the segment.
            - "segment_start_time" (float | int): Start time of the segment in seconds.
            - "segment_end_time" (float | int): End time of the segment in seconds.
            - "distance" (float): Distance or relevance score for the segment.
    Returns:
        list[dict]: A list of dictionaries (as produced by SegmentWithVideoIDModel.model_dump()), where each dictionary
        has the keys:
            - "video_id": The video identifier.
            - "segments": A list of segment dictionaries (from VideoSegmentModel), each containing
              "segment_text", "segment_start_time", "segment_end_time", and "distance".
    """

    try:
        grouped = defaultdict(list)

        for item in raw_segments:
            video_id = item["video_id"]
            segment_data = {
                "segment_text": item["segment_text"],
                "segment_start_time": item["segment_start_time"],
                "segment_end_time": item["segment_end_time"],
                "distance": item["distance"],
            }
            grouped[video_id].append(VideoSegmentModel(**segment_data))

        results = [
            SegmentWithVideoIDModel(video_id=video_id, segments=segments).model_dump()
            for video_id, segments in grouped.items()
        ]

        return results
    except Exception as e:
        logger.error(f"Unable to group result based on video id: {e}")
        raise


class VideoSEOQueryAdapter(VideoSEOQueryPort):
    def __init__(
        self,
        database_port: PostgresDatabasePort,
        openai_client_port: AsyncOpenAIAPIPort,
    ):
        self.database_port = database_port
        self.openai_client_port = openai_client_port

    async def async_get_video_seo_query(
        self, query: str, chat_id: UUID, temporary_id: Optional[str] = None
    ) -> VideoSEOResponseModel:
        """
        Generate a video SEO search response by embedding the input query
        and retrieving the most similar video segments from the database.

        Args:
            query (str): The natural language search query provided by the user.
            chat_id (str): The chat id (unique user id) of the user.
            temporary_id (str): The temporary id  of the user.
        Returns:
            VideoSEOResponseModel:
                A Pydantic response object containing:
                - status: "success" or "error"
                - results: List of top-K similar video segment responses
                - error: Error message if an issue occurs, otherwise None
        Raises:
            Exception: Propagates unexpected exceptions that occur during
                    OpenAI embedding generation or database operations.
        """
        try:
            if query == "" or not query:
                logger.error("No query provided")
                return VideoSEOResponseModel.model_validate(
                    {
                        "status": "Error",
                        "results": [],
                        "error": "Query is empty or None",
                    }
                ).model_dump()

            if not chat_id:
                logger.error("chat_id is empty")
                return VideoSEOResponseModel.model_validate(
                    {
                        "status": "Error",
                        "results": [],
                        "error": "chat_id is empty",
                    }
                ).model_dump()

            embeddings = await self.openai_client_port.text_embedding(
                text=query, model="text-embedding-3-small"
            )

            if not embeddings:
                logger.error("No embedding found")
                return VideoSEOResponseModel.model_validate(
                    {
                        "status": "Error",
                        "results": [],
                        "error": "Embedding is empty or None",
                    }
                ).model_dump()
            query_embedding = embeddings[0]
            print("the type of query embeddding is", type(query_embedding))

            results = await self.database_port.search_similar_vectors(
                query_embedding=query_embedding,
                top_k=250,
                similarity_algorithm="cosine",
            )

            grouped_results = group_segments_by_video_id(raw_segments=results)
            if grouped_results:
                created_time = datetime.now(timezone.utc)
                print("the current created utc time is", created_time)
                try:
                    await self.database_port.insert_into_session_table(
                        chat_id=str(chat_id),
                        temporary_id=temporary_id,
                        response=grouped_results,
                        query= query,
                        created_at= created_time
                    )
                except Exception as e:
                    logger.error(f"Error occurred while inserting response into seo_response_history_table: {e}")

            schema = VideoSEOResponseModel.model_validate({"results": grouped_results})
            return schema.model_dump(exclude_none=True)
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            logger.error(f"{error_message}")
            return VideoSEOResponseModel.model_validate(
                {"status": "Error", "results": [], "error": error_message}
            ).model_dump()
