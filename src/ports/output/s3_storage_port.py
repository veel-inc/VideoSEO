# from abc import ABC, abstractmethod
# from typing import Dict, Any
# from pathlib import Path

# class S3StoragePort(ABC):
#     """Abstract base class for S3 storage ports"""

#     @abstractmethod
#     async def download_from_s3(self, bucket_name:str, object_key:str) -> tuple[Path, float]:
#         """Asynchronously downloads a file from the S3 bucket
#         Args:
#             :param bucket_name: S3 bucket name
#             :param object_key: S3 object key
#         Returns:
#             Dict[str, float]: Dictionary of local file path and time taken to download the file
#             """
#         pass

    # @abstractmethod
    # async def upload_to_s3(self, local_path:Path, bucket_name:str, s3_prefix:str)-> tuple[Path, float]:
    #     """Asynchronously uploads a local file to the S3 bucket
    #     Args:
    #         :param local_path: Local file path or directory to upload
    #         :param bucket_name: S3 bucket name where the file is to be uploaded
    #         :param s3_prefix: S3 prefix
    #     Returns:
    #         Dict[str, float]: Dictionary of local file path and time taken to upload the file
    #         """
    #     pass