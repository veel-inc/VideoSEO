from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorModel(BaseModel):
    download_error: Optional[str] = Field(None, description="s3 Object download error")
    file_type_error: Optional[str] = Field(
        None, description="Downloaded File Type error"
    )
    exception_error: Optional[str] = Field(None, description="Exception error.")


class VideoSegmentModel(BaseModel):
    segment_text: str = Field(..., description="extracted segmented text")
    segment_start_time: float = Field(
        ..., description="Start time of each video segments"
    )
    segment_end_time: float = Field(..., description="End time of each video segments")
    distance: float = Field(
        ..., description="confindence score that calculates the distance to other query"
    )


class SegmentWithVideoIDModel(BaseModel):
    video_id: str = Field(..., description="Unique video id")
    segments: Optional[List[VideoSegmentModel]] = Field(
        None, description="List of each segments from the model"
    )


class VideoSEOResponseModel(BaseModel):
    status: Optional[str] = Field(
        default="Success", description="status success or error of the result"
    )
    results: Optional[List[SegmentWithVideoIDModel]] = Field(
        default_factory=list, description="List of video seo query responses"
    )
    error: Optional[str] = Field(None, description="error message")
