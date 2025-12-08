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
from pathlib import Path
from typing import Any, Dict, List

from src.domain.models import VideoDatabaseModel, VideoSegmentDatabaseModel
from src.ports.output import AsyncOpenAIAPIPort
from src.utils import extract_audio_from_video, file_exists_and_nonempty, get_media_type

logger = logging.getLogger(__name__)


class AudioTranscribeAndEmbedService:
    def __init__(
        self,
        openai_api_port: AsyncOpenAIAPIPort,
    ):
        self.openai_api_port = openai_api_port

    async def _download_and_extract_audio(self, video_path: Path) -> Dict[str, Any]:
        try:
            logger.info(f"video downloaded: {video_path}")
            if not video_path or not await file_exists_and_nonempty(video_path):
                error_message = f"Input file missing or empty: {str(video_path)}"
                logger.error(f"{error_message}")
                return {"status": "error", "error": error_message}
            logger.info("checking for media type")  ##
            media_type = await get_media_type(video_path)
            if media_type != "video":
                error_message = f"Unsuitable file type [{media_type}]"
                logger.error(f"{error_message}")
                return {"status": "error", "error": error_message}

            audio_path = await extract_audio_from_video(video_path=str(video_path))
            if not audio_path or not await file_exists_and_nonempty(audio_path):
                error_message = f"Input file missing or empty: {str(video_path)}"
                logger.error(f"{error_message}")
                return {"status": "error", "error": error_message}
            logger.info(f"the audio path is: {audio_path} ")
            return {"status": "success", "audio_path": audio_path}

        except Exception:
            logger.info("An unexpected error occurred")
            return {"status": "error", "error": "An Unexpected error occurred"}

    async def _get_transcription(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Generate transcriptions for the given audio file using OpenAI Whisper API.

        Args:
                audio_file_path (str): Path to the audio file
        Returns:
                list[dict]: List of sentence segments with start time, end time, and sentence text
        """

        try:
            transcript_response = await self.openai_api_port.audio_transcription(
                audio_path=audio_file_path,
                model="whisper-1",
                timestamp_granularities=["segment"],
            )
        except Exception as e:
            error_message = f"Failed to get transcription. {e}"
            logger.error(f"{error_message}")
            raise RuntimeError(f"Failed to get transcription: {e}") from e

        sentence_segments = [
            {
                # "start_time": second_converter(seg["start"]),
                # "end_time": second_converter(seg["end"]),
                "index": i + 1,
                "start_time": (seg["start"]),
                "end_time": (seg["end"]),
                "sentence": seg["text"].strip(),
            }
            for i, seg in enumerate(transcript_response.get("segments", []))
        ]

        logger.info(f"transcribed each segments: {sentence_segments}")

        full_transcription = " ".join(
            seg["text"].strip() for seg in transcript_response.get("segments", [])
        )
        return {"full_text": full_transcription, "segments": sentence_segments}

    async def _embed_full_text(self, full_transcribed_text: str) -> List:
        """
        Generate Embedding of the full transcribed text of the audio.

        Args:
                full_transcribed_text (str): complete text that was transcribed from the video
        Returns:
                list: List of embedding
        """

        try:
            embedded_full_text = await self.openai_api_port.text_embedding(
                text=full_transcribed_text, model="text-embedding-3-small"
            )
            return embedded_full_text
        except Exception as e:
            error_message = f"Failed to get embedding: {e}"
            logger.error(f"{error_message}")
            raise RuntimeError(f"Failed to get embeddings: {e}") from e

    async def _embed_text_segments(self, segments: List):
        """
        Generate Embedding of the full transcribed text of the audio.

        Args:
                full_transcribed_text (str): complete text that was transcribed from the video
        Returns:
                list: List of embedding
        """
        try:
            embedded_segments = []
            for idx, seg in enumerate(segments):
                embedded_segment = await self.openai_api_port.text_embedding(
                    text=seg.get("sentence"), model="text-embedding-3-small"
                )
                if embedded_segment:
                    embedded_segments.append(
                        {"index": idx + 1, "embedding": embedded_segment or []}
                    )

            return embedded_segments

        except Exception as e:
            error_message = f"Failed to get embedding: {e}"
            logger.error(f"{error_message}")
            raise RuntimeError(f"Failed to get embeddings: {e}") from e

    async def process_video(
        self,
        video_path: Path,
        video_id: str,
        tenant_id: str,
        video_url: str,
        title: str | None = None,
        metadata: dict | None = None,
    ):
        result = await self._download_and_extract_audio(video_path=video_path)
        if result.get("status") != "success":
            return {"status": "error", "error": "Error occurred"}
        audio_path = result.get("audio_path", "")

        transcription = await self._get_transcription(audio_file_path=audio_path)

        full_text_embedding = await self._embed_full_text(transcription["full_text"])
        segment_embeddings = await self._embed_text_segments(transcription["segments"])
        print("the length of segnment embedding are", len(segment_embeddings))

        logger.info(f"Completed transcription and embedding for video_id: {video_id}")

        complete_video_record = VideoDatabaseModel(
            video_id=video_id,
            tenant_id=tenant_id,
            title=title,
            video_url=video_url,
            video_metadata=metadata,
            video_text=transcription["full_text"],
            text_embedding=full_text_embedding,
        )

        segments_record = []

        for seg, emb in zip(transcription["segments"], segment_embeddings):
            segments_record.append(
                VideoSegmentDatabaseModel(
                    video_id=video_id,
                    tenant_id=tenant_id,
                    segment_index=seg.get("index", 0),
                    segment_start_time=str(seg["start_time"]),
                    segment_end_time=str(seg["end_time"]),
                    segment_text=seg["sentence"],
                    segment_embedding=emb["embedding"],
                ).model_dump()
            )

        return complete_video_record.model_dump(), segments_record
