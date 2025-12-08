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

from typing import Optional

import strawberry
from strawberry.experimental import pydantic

from src.adapters import (
    AsyncOpenAIApiAdapter,
    AsyncPostgresDatabaseAdapter,
    HealthServiceAdapter,
    TrendingSearchAdapter,
    VideoSEOQueryAdapter,
)
from src.domain.models import (
    HealthResponseModel,
    PopularVideosRequestModel,
    PopularVideosResponseModel,
    SegmentWithVideoIDModel,
    TrendingSearchModel,
    TrendingSearchRequestModel,
    TrendingSearchResponseModel,
    VideoSegmentModel,
    VideoSEOQueryRequestModel,
    VideoSEOResponseModel,
)

adapter = HealthServiceAdapter()


@strawberry.experimental.pydantic.type(model=HealthResponseModel, all_fields=True)
class HealthResponseType:
    pass


@pydantic.type(model=VideoSegmentModel, all_fields=True)
class VideoSegmentType:
    pass


@pydantic.type(model=SegmentWithVideoIDModel, all_fields=True)
class SegmentWithVideoIDType:
    pass


@pydantic.type(model=VideoSEOResponseModel, all_fields=True)
class VideoSEOResponseType:
    pass


@pydantic.input(model=VideoSEOQueryRequestModel, all_fields=True)
class VideoSEORequestType:
    pass


@pydantic.type(model=TrendingSearchModel, all_fields=True)
class TrendingSearchType:
    """GraphQL type for a single trending search."""

    pass


@pydantic.input(model=TrendingSearchRequestModel, all_fields=True)
class TrendingSearchRequestType:
    """GraphQL input for requesting trending searches."""

    pass


@pydantic.type(model=TrendingSearchResponseModel, all_fields=True)
class TrendingSearchResponseType:
    """GraphQL response type for trending searches."""

    pass


@pydantic.input(model=PopularVideosRequestModel, all_fields=True)
class PopularVideosRequestType:
    pass


@pydantic.type(model=PopularVideosResponseModel, all_fields=True)
class PopularVideosResponseType:
    pass


@strawberry.type
class Query:
    @strawberry.field
    async def health_check(self) -> HealthResponseType:
        """
        Check if the service is running.
        Args:
            None

        Returns:
            HealthResponseType: The health status of the service.
        """
        response = await adapter.is_service_running()
        return HealthResponseType.from_pydantic(response)

    @strawberry.field
    async def search_video_connections(
        self, video_seo_request: VideoSEORequestType
    ) -> VideoSEOResponseType:
        database_adapter = AsyncPostgresDatabaseAdapter()
        openai_adapter = AsyncOpenAIApiAdapter()

        run_seo_query = VideoSEOQueryAdapter(
            database_port=database_adapter, openai_client_port=openai_adapter
        )

        video_seo_result = await run_seo_query.async_get_video_seo_query(
            chat_id=video_seo_request.chat_id,
            query=video_seo_request.query,
            temporary_id=video_seo_request.temporary_id,
        )

        validated_video_seo_result = VideoSEOResponseModel.model_validate(
            video_seo_result
        )
        return VideoSEOResponseType.from_pydantic(validated_video_seo_result)

    @strawberry.field
    async def get_trending_searches(
        self, request: TrendingSearchRequestType
    ) -> TrendingSearchResponseType:
        """Get current trending searches."""
        try:
            database_adapter = AsyncPostgresDatabaseAdapter()
            openai_adapter = AsyncOpenAIApiAdapter()

            pipeline = TrendingSearchAdapter(
                database_port=database_adapter, openai_client_port=openai_adapter
            )

            result = await pipeline.get_current_trends(
                limit=request.limit, min_score=request.min_score
            )

            validated = TrendingSearchResponseModel.model_validate(result)
            return TrendingSearchResponseType.from_pydantic(validated)

        except Exception as e:
            error_response = TrendingSearchResponseModel(
                status="error", trending_searches=[], error=str(e)
            )
            return TrendingSearchResponseType.from_pydantic(error_response)

    @strawberry.field
    async def get_popular_videos(
        self, popular_video_request: PopularVideosRequestType
    ) -> PopularVideosResponseType:
        try:
            database_adapter = AsyncPostgresDatabaseAdapter()

            result = await database_adapter.search_popular_videos(
                limit= popular_video_request.limit
            )
            validated = PopularVideosResponseModel.model_validate({
                "status":"success",
                "popular_videos": result,
                "error": None
            })
            return PopularVideosResponseType.from_pydantic(validated)
        except Exception as e:
            error_response = PopularVideosResponseModel(
                status="error", popular_videos=[], error=str(e)
            )
            return PopularVideosResponseType.from_pydantic(error_response)
