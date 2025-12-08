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
from typing import List, Optional, Dict, Any, Union, Type
from pydantic import BaseModel

from dotenv import load_dotenv
from openai import AsyncClient
from openai.types.audio import TranscriptionVerbose
from openai.types.responses import Response

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
            logger.error(f"Unexpected error occurred during embedding: {e}")
            raise

    async def response(
        self,
        user_input: Union[str, List[Dict[str, str]]],
        instructions: str,
        model: str = ResponseConfig.DEFAULT_MODEL,
        temperature: float = ResponseConfig.DEFAULT_TEMPERATURE,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = ResponseConfig.TOOL_CHOICE_AUTO,
    ) -> Response:
        """
        Generate a response from the AI model.

        Args:
            user_input: The user input as a string or list of message dictionaries
            instructions: System instructions for the model
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 1.0)
            tools: Optional list of tool definitions
            tool_choice: Tool selection strategy ('auto', 'required', or 'none')

        Returns:
            Response dictionary from the API

        Raises:
            ValueError: If parameters are invalid
        """
        if not 0.0 <= temperature <= 1.0:
            raise ValueError(
                f"Temperature must be between 0.0 and 1.0, got {temperature}"
            )

        params: Dict[str, Any] = {
            "model": model,
            "input": user_input,
            "instructions": instructions,
        }

        if model not in ResponseConfig.MODELS_WITHOUT_TEMPERATURE:
            params["temperature"] = temperature

        if tools:
            params["tools"] = tools
            params["tool_choice"] = tool_choice

        logger.info(f"Making API call with model: {model}")

        try:
            response = await self.client.responses.create(**params)
            logger.debug(f"API call successful for model: {model}")
            return response
        except Exception as e:
            logger.error(f"API call failed for model {model}: {str(e)}")
            raise

    async def structured_response(
        self,
        user_input: Union[str, List[Dict[str, str]]],
        instructions: str,
        schema_model: Type[BaseModel],
        model: str = ResponseConfig.DEFAULT_MODEL,
        temperature: float = ResponseConfig.DEFAULT_TEMPERATURE,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Response:
        """
        Generate a structured response conforming to a Pydantic schema.

        Args:
            user_input: The user input as a string or list of message dictionaries
            instructions: System instructions for the model
            schema_model: Pydantic model class defining the expected structure
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 1.0)
            tools: Optional list of tool definitions (auto-generated if not provided)

        Returns:
            Structured response matching the schema_model

        Raises:
            ValueError: If schema_model is not a Pydantic BaseModel
        """
        if not issubclass(schema_model, BaseModel):
            raise ValueError(
                f"schema_model must be a Pydantic BaseModel, got {type(schema_model)}"
            )

        if tools is None:
            schema_name = schema_model.__name__
            tools = [
                {
                    "type": "function",
                    "name": f"get_{schema_name.lower()}_data",
                    "description": f"Generate structured data conforming to {schema_name} schema",
                    "parameters": schema_model.model_json_schema(),
                },
            ]
            logger.debug(f"Auto-generated tool definition for {schema_name}")

        return await self.response(
            user_input=user_input,
            instructions=instructions,
            model=model,
            temperature=temperature,
            tools=tools,
            tool_choice=ResponseConfig.TOOL_CHOICE_REQUIRED,
        )