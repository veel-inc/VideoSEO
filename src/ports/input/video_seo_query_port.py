from abc import ABC, abstractmethod
from uuid import UUID
from typing import Optional
from src.domain.models import VideoSEOResponseModel


class VideoSEOQueryPort(ABC):
    """Abstract class to get query for video seo"""

    @abstractmethod
    async def async_get_video_seo_query(self, query: str,chat_id: UUID, temporary_id: Optional[str] = None) -> VideoSEOResponseModel:
        pass
