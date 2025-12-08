from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VideoDatabaseModel(BaseModel):
    video_id: str = Field(..., description="unique video id")
    tenant_id: str = Field(..., description="unique org id")
    title: Optional[str] = Field(None, description="title of the video")
    video_url: Optional[str] = Field(None, description="s3 url of the video")
    video_metadata: Optional[Dict[str, Any]] = Field(
        None, description="metadata of the video"
    )
    video_text: str = Field(..., description="full text of the video")
    text_embedding: List = Field(
        ..., description="complete embedding of the video text"
    )


class VideoSegmentDatabaseModel(BaseModel):
    video_id: str = Field(..., description="unique video id")
    tenant_id: str = Field(..., description="unique org id")
    segment_index: int = Field(..., description="unique indexing of the segment")
    segment_start_time: float = Field(
        ..., description="Start time of the particular segments"
    )
    segment_end_time: float = Field(..., description="End time for particular segments")
    segment_text: str = Field(
        ..., description="individual sentence level transcripted text"
    )
    segment_embedding: List = Field(
        ..., description="embedding of each individual text"
    )
