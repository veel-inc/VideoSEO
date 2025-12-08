from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal
from openai.types.audio import TranscriptionVerbose


class AsyncOpenAIAPIPort(ABC):
    """Abstract base class for asynchronous OpenAI API ports"""

    @abstractmethod
    async def audio_transcription(
        self,
        audio_path: str,
        model: str,
        timestamp_granularities: list[Literal["segment", "word"]] | None,
    ) -> TranscriptionVerbose:
        pass

    @abstractmethod
    async def text_embedding(
        self, text: str | List[Dict[str, Any]], model: str
    ) -> List[str]:
        pass
