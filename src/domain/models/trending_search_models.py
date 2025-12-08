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
from datetime import datetime
from pydantic import BaseModel, Field

class TrendingSearchModel(BaseModel):
    """Individual trending search result."""
    query: str = Field(..., description="Representative search query")
    trend_score: float = Field(..., description="Trend score (higher = more trending)")
    query_count: int = Field(..., description="Total queries in this cluster")
    unique_query_count: int = Field(..., description="Number of unique query variations")
    top_queries: str = Field(..., description="Most common query variations")
    created_at: datetime = Field(..., description="When this trend was identified")
    batch_timestamp: datetime = Field(..., description="Batch processing timestamp")

class TrendingSearchRequestModel(BaseModel):
    """Request parameters for fetching trending searches."""
    limit: Optional[int] = Field(20, ge=1, le=100, description="Maximum trends to return")
    min_score: Optional[float] = Field(0.0, ge=0.0, description="Minimum trend score threshold")

class ExtendedTrendingSearchResponseModel(BaseModel):
    """Response containing list of trending searches."""
    status: str = Field(default="success", description="Response status")
    trends: List[TrendingSearchModel] = Field(default_factory=list, description="List of trending searches")
    count: int = Field(default=0, description="Number of trends returned")
    error: Optional[str] = Field(None, description="Error message if any")

class RepresentativeQueryModel(BaseModel):
    """Model for a representative trending search query."""
    query: str = Field(..., description="Representative search query")

class TrendingSearchResponseModel(BaseModel):
    status: Optional[str] = Field(
        None, description="Status of the Trending Searches Retrieval"
    )    
    trending_searches: List[str] = Field(..., description="List of decorated trending search queries")
    error: Optional[str] = Field(None, description="Error message if any")