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
from pathlib import Path
from typing import Any, Dict


class S3StoragePort(ABC):
    """Abstract base class for S3 storage ports"""

    @abstractmethod
    async def download_from_s3(
        self, bucket_name: str, object_key: str
    ) -> tuple[Path, float]:
        """Asynchronously downloads a file from the S3 bucket
        Args:
            :param bucket_name: S3 bucket name
            :param object_key: S3 object key
        Returns:
            Dict[str, float]: Dictionary of local file path and time taken to download the file
        """
        pass

    @abstractmethod
    async def upload_to_s3(
        self, local_path: Path, bucket_name: str, s3_prefix: str
    ) -> tuple[Path, float]:
        """Asynchronously uploads a local file to the S3 bucket
        Args:
            :param local_path: Local file path or directory to upload
            :param bucket_name: S3 bucket name where the file is to be uploaded
            :param s3_prefix: S3 prefix
        Returns:
            Dict[str, float]: Dictionary of local file path and time taken to upload the file
        """
        pass
