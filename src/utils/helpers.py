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

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CURRENT_DIR = Path(__file__).resolve().parent
AUDIO_DIR = CURRENT_DIR / ".." / ".." / "media" / "audio"


async def run_ffmpeg_command(command: list[str]) -> dict[str, Any]:
    """
    Helper function to run ffmpeg command and return the results

    Args:
        command: List of ffmpeg commands to run
    Returns:
        dict: Structured result
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode(errors="replace").strip()
            logger.error(f"ffmpeg failed: {error_msg}")
            return {"status": "error", "error": error_msg, "output": None}
        else:
            logger.info("ffmpeg completed successfully")
            return {
                "status": "success",
                "output": stdout.decode().strip(),
                "error": None,
            }

    except Exception as e:
        logger.exception(f"Exception during ffmpeg execution: {e}")
        return {"status": "error", "error": str(e), "output": None}


async def extract_audio_from_video(video_path: str) -> str | dict[str, Any] | None:
    """
    Helper function to extract audio from video file

    Args:
        video_path: Path to video file
    Returns:
        str: Path to extracted audio file
        dict[str, Any]: Error details if extraction fails
        None: If an unexpected exception occurs
    """
    await asyncio.to_thread(AUDIO_DIR.mkdir, parents=True, exist_ok=True)
    logger.info(f"Extracting audio from {video_path}")
    video_path = Path(video_path)

    audio_path = str(AUDIO_DIR / f"{video_path.stem}.mp3")
    try:
        audio_cmd = [
            "ffmpeg",
            "-i",
            video_path,
            "-q:a",
            "0",
            "-map",
            "a",
            audio_path,
            "-y",
        ]
        result = await run_ffmpeg_command(audio_cmd)

        if result["status"] == "success":
            logger.info("Audio extracted successfully")
            return audio_path
        else:
            try:
                await asyncio.to_thread(
                    lambda: AUDIO_DIR.rmdir() if AUDIO_DIR.exists() else None
                )
            except OSError:
                pass
    except Exception as e:
        logger.exception(f"Exception during ffmpeg execution: {e}")


async def file_exists_and_nonempty(file_path: Path) -> bool:
    """
    Helper function to check if a file exists and non-empty

        :param file_path: Path to the file

        :return: True if the file exists and non-empty, False otherwise
    """

    def _sync_check():
        p = Path(file_path)
        return p.exists() and p.stat().st_size > 0

    return await asyncio.to_thread(_sync_check)


async def get_media_type(file_path: Path):
    """
    Determine if the file is video, audio, or image based on extension.

    :param file_path: Path to the media file
    :return: 'video', 'audio', 'image', or None if unknown
    """
    VIDEO_EXTENSIONS = {
        ".mp4",
        ".avi",
        ".mov",
        ".mkv",
        ".flv",
        ".wmv",
        ".webm",
        ".m4v",
        ".mpeg",
        ".mpg",
    }
    AUDIO_EXTENSIONS = {
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".m4a",
        ".wma",
        ".opus",
        ".aiff",
    }
    IMAGE = {".png", ".jpg", ".jpeg", ".webp"}

    def _check_type():
        extension = file_path.suffix.lower()
        if extension in VIDEO_EXTENSIONS:
            return "video"
        elif extension in AUDIO_EXTENSIONS:
            return "audio"
        elif extension in IMAGE:
            return "image"
        else:
            return None

    return await asyncio.to_thread(_check_type)
