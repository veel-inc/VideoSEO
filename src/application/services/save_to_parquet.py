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

import pandas as pd
import logging
from pathlib import Path
import os

from src.application.services.audio_transcribe_embed_service import (
    AudioTranscribeAndEmbedService,
)
from src.adapters import AsyncOpenAIApiAdapter

logger = logging.getLogger(__name__)

CURR_DIR = Path(__file__).resolve().parent
PARQUET_DIR = CURR_DIR.parents[2] / "media" / "parquet_files"

# Create parquet_files directory if not exists
PARQUET_DIR.mkdir(parents=True, exist_ok=True)

obj = AudioTranscribeAndEmbedService(openai_api_port=AsyncOpenAIApiAdapter())


async def save_video_data(
    tenant_id: str,
    video_url:str |None=None,
    title: str | None = None,
    metadata: dict | None = None,
):
    video_dir = "your-video-directory-path"
    list_dir = os.listdir(video_dir)

    for idx, file_path in enumerate(list_dir):
        video_file = Path(f"{video_dir}/{file_path}")

        print("len and path in list", len(list_dir), list_dir)
        video_id = video_file.stem
        complete_res, segment_res = await obj.process_video(
            video_path=video_file,
            video_id=video_id,
            tenant_id=tenant_id,
            title= f"video_{idx+1}_test_nuvia",
            video_url=video_url,
            metadata=metadata,
        )

        complete_data = pd.DataFrame([complete_res])
        complete_file_path = PARQUET_DIR / f"video_{video_id}.parquet"
        complete_data.to_parquet(complete_file_path)
        logger.info("complete data saved as parquet")

        segment_data = pd.DataFrame(segment_res)
        segment_file_path = PARQUET_DIR / f"segment_{video_id}.parquet"

        segment_data.to_parquet(segment_file_path)
        logger.info("segments saved as parquet")
    return "File saved"

