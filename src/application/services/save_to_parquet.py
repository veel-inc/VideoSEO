import pandas as pd
import logging
from pathlib import Path
import os

# from src.core import setup_logging
from src.application.services.audio_transcribe_embed_service import (
    AudioTranscribeAndEmbedService,
)
from src.adapters import AsyncOpenAIApiAdapter

# setup_logging()
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
    video_dir = "/home/yogesh/Desktop/ugc_videos"
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

