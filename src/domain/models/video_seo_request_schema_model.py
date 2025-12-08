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
