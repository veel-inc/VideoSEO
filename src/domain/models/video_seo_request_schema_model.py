from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VideoSEORequestSchemaModel(BaseModel):
    video_id: str = Field(..., description="Unique ID of the video")
    tenant_id: str = Field(..., description="Unique id of the org (tenant id)")
    title: str = Field(..., description="Ttile of the video")
    bucket_name: str = Field(
        ..., description="s3 bucket name of the video where it is stored"
    )
    object_key: str = Field(..., description="S3 object key of the video")
    video_metadata: str = Field(
        ..., description="metadata of the video (eg: duration, uploaded date etc..)"
    )


class VideoSEOQueryRequestModel(BaseModel):
    chat_id: UUID = Field(..., description="Unique chat id of the user")
    temporary_id: Optional[str] = Field(None, description= "Temporary id to store query of unauthenticated user")
    query: str = Field(..., description="searched text in the search bar")
