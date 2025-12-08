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
