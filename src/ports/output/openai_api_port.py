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

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional, Union, Type
from openai.types.responses import Response
from openai.types.audio import TranscriptionVerbose
from pydantic import BaseModel

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

    @abstractmethod
    async def response(
        self,
        user_input: Union[str, List[Dict[str, str]]],
        instructions: str,
        model: str,
        temperature: float,
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: str,
    ) -> Response:
        pass
    
    @abstractmethod
    async def structured_response(
        self,
        user_input: Union[str, List[Dict[str, str]]],
        instructions: str,
        schema_model: Type[BaseModel],
        model: str,
        temperature: float,
        tools: Optional[List[Dict[str, Any]]],
    ) -> Response:
        pass
