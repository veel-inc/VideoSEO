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

import logging
import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from openai import AsyncClient
from openai.types.audio import TranscriptionVerbose

from src.ports.output import AsyncOpenAIAPIPort
from src.utils import SingletonABCMeta

load_dotenv()

logger = logging.getLogger(__name__)


class ResponseConfig:
    """
    Configuration for response generation.
    """

    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_TEMPERATURE = 0.6
    TOOL_CHOICE_AUTO = "auto"
    TOOL_CHOICE_REQUIRED = "required"
    MODELS_WITHOUT_TEMPERATURE = ["gpt-5", "gpt-5-mini"]


class AsyncOpenAIApiAdapter(AsyncOpenAIAPIPort, metaclass=SingletonABCMeta):
    """
    A wrapper class for OpenAI's AsyncClient that simplifies making API calls.
    """

    def __init__(self):
        self.openai_api_key = os.getenv(
            "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", None)
        )

        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API Key must be provided via environment variables or .env file"
            )

        self.client = AsyncClient(api_key=self.openai_api_key)

    async def audio_transcription(
        self,
        audio_path: str,
        model: str = "whisper-1",
        timestamp_granularities: Optional[List[str]] = None,
    ) -> TranscriptionVerbose:
        """
        Transcribe audio file to text with timestamps.

        Args:
            audio_path: Path to the audio file
            model: Transcription model to use (default: whisper-1)
            timestamp_granularities: Timestamp levels, e.g. ["word", "segment"]

        Returns:
            Dictionary with transcription text and timestamps

        Raises:
            FileNotFoundError: If audio file doesn't exist
        """

        if timestamp_granularities is None:
            timestamp_granularities = ["segment"]

        audio_file = Path(audio_path)
        # Basic validation
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing: {audio_file.name} with model {model}")

        try:
            with open(audio_path, "rb") as f:
                response = await self.client.audio.transcriptions.create(
                    file=f,
                    model=model,
                    response_format="verbose_json",
                    timestamp_granularities=timestamp_granularities,
                )

            return response.model_dump()

        except Exception as e:
            logger.error(f"Transcription failed for {audio_file.name}: {e}")
            raise

    async def text_embedding(self, text: str, model: str = "text-embedding-3-small"):
        """
        Perform embedding of the given text.
        Args:
            text: transcribed text to embed
            model: Embedding model to use (default: text-embedding-3-small)
        Returns:
            List of embeddings
        """

        if not text:
            raise ValueError("Text input is empty or None for embedding")

        logger.info("Embedding the text or text segments")

        try:
            response = await self.client.embeddings.create(
                input=text,
                model=model,
            )

            embeddings = [item.embedding for item in response.data]
            return embeddings
        except Exception as e:
            logger.error(f"Unexpected error occured during embedding: {e}")
            raise
