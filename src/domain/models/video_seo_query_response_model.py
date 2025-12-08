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
        ..., description="confidence score that calculates the distance to other query"
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
