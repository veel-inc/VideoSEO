import strawberry
from strawberry.experimental import pydantic

from src.adapters import (
    AsyncOpenAIApiAdapter,
    AsyncPostgresDatabaseAdapter,
    HealthServiceAdapter,
    VideoSEOQueryAdapter,
)
from src.domain.models import (
    HealthResponseModel,
    SegmentWithVideoIDModel,
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
            chat_id=video_seo_request.chat_id, query=video_seo_request.query,
            temporary_id= video_seo_request.temporary_id
        )

        validated_video_seo_result = VideoSEOResponseModel.model_validate(
            video_seo_result
        )
        return VideoSEOResponseType.from_pydantic(validated_video_seo_result)
