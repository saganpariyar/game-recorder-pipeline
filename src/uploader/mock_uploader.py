"""Mock Uploader for testing and dry runs without requiring Google Cloud credentials."""

import logging
from typing import List, Optional
from src.uploader.base import BaseUploader

logger = logging.getLogger("Pipeline.MockUploader")


class MockUploader(BaseUploader):
    """Simulates YouTube upload without connecting to Google APIs."""

    def __init__(self):
        super().__init__(name="MockUploader")

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        privacy_status: str = "unlisted",
        category_id: str = "20",
        made_for_kids: bool = False,
        thumbnail_path: Optional[str] = None,
        publish_at: Optional[str] = None
    ) -> str:
        logger.info(f"[MOCK UPLOAD] Simulating YouTube upload for: {video_path}")
        logger.info(f"  Title: {title}")
        logger.info(f"  Privacy: {privacy_status}")
        logger.info(f"  Category: {category_id}")
        logger.info(f"  Tags: {tags}")
        mock_id = "mock_" + str(abs(hash(video_path)))[:8]
        mock_url = f"https://youtu.be/{mock_id}"
        logger.info(f"[MOCK UPLOAD SUCCESS] Simulated Video URL: {mock_url}")
        return mock_url

