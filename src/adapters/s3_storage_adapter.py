import asyncio
import logging
import os
import time
from pathlib import Path

import aioboto3
from dotenv import load_dotenv

from src.ports.output import S3StoragePort

CURRENT_DIR = Path(__file__).resolve().parent
VIDEO_DIR = CURRENT_DIR / ".." / ".." / "media" / "downloaded"

load_dotenv()

logger = logging.getLogger(__name__)


class S3StorageAdapter(S3StoragePort):
    """Implement the S3 Storage Port to handle S3 interactions asynchronously."""

    def __init__(self):
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION")

        if (
            not self.aws_secret_access_key
            or not self.aws_access_key_id
            or not self.aws_region
        ):
            logger.error("AWS credentials or region not set in environment variables.")
            raise ValueError(
                "AWS credentials or region not set in environment variables."
            )

        self.session = aioboto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region,
        )

    async def download_from_s3(
        self, bucket_name: str, object_key: str
    ) -> tuple[Path, float]:
        """
        Asynchronously download a file from an S3 bucket and save it to the 'videos' folder.
        Args:
                bucket_name (str): The name of the S3 bucket.
                object_key (str): The key of the object to download.
        Returns:
                tuple[str, float]: A tuple containing the local file path and the time taken to download in seconds
        """
        start_time = time.time()
        logger.info(f"Downloading {object_key} from {bucket_name}")
        await asyncio.to_thread(VIDEO_DIR.mkdir, parents=True, exist_ok=True)

        filename = Path(object_key).name
        local_path = VIDEO_DIR / filename

        async with self.session.client("s3") as s3:
            await s3.download_file(bucket_name, object_key, str(local_path))

        end_time = time.time()
        logger.info(f"Downloaded {object_key} in {end_time - start_time} seconds.")
        return local_path, end_time - start_time
