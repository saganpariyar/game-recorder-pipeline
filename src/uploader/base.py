"""Base Uploader interface for Stage 3: YouTube Upload."""

from abc import ABC, abstractmethod
from typing import List, Optional


class BaseUploader(ABC):
    """Abstract base class for uploading recorded videos."""

    def __init__(self, name: str = "BaseUploader"):
        self.name = name

    @abstractmethod
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
        """Upload video file and return public/unlisted YouTube video URL."""
        pass

