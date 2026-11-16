"""YouTube Data API v3 uploader with OAuth 2.0 and resumable chunked upload."""

import os
import time
import logging
from pathlib import Path
from typing import List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from src.uploader.base import BaseUploader
from src.config_loader import YouTubeConfig

logger = logging.getLogger("Pipeline.YouTubeUploader")

# YouTube Upload Scope
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube"
]


class YouTubeUploader(BaseUploader):
    """Handles OAuth 2.0 authentication, token refresh, and resumable video uploads to YouTube."""

    def __init__(self, config: YouTubeConfig):
        super().__init__(name="YouTubeUploader")
        self.config = config
        self.youtube = None

    def authenticate(self):
        """Perform OAuth2 authorization or load cached tokens from disk."""
        creds = None
        project_root = Path(__file__).parent.parent.parent.resolve()

        token_path = Path(self.config.token_cache_file)
        if not token_path.is_absolute():
            token_path = (project_root / token_path).resolve()

        secrets_path = Path(self.config.client_secrets_file)
        if not secrets_path.is_absolute():
            secrets_path = (project_root / secrets_path).resolve()

        # 1. Load cached token if available
        if token_path.is_file():
            try:
                creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
                logger.info(f"Loaded cached YouTube OAuth credentials from: {token_path}")
            except Exception as e:
                logger.warning(f"Failed to read existing token cache: {e}. Will re-authenticate.")
                creds = None

        # 2. Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Cached token expired. Refreshing OAuth token silently...")
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}. Running full auth flow...")
                    creds = None

            if not creds:
                if not secrets_path.is_file():
                    err_msg = (
                        f"OAuth Client Secrets file not found at: {secrets_path.resolve()}\n\n"
                        "To upload automatically to YouTube, follow these 4 quick steps:\n"
                        "  1. Go to Google Cloud Console (https://console.cloud.google.com/)\n"
                        "  2. Enable 'YouTube Data API v3'.\n"
                        "  3. Create Credentials -> OAuth client ID (Application type: Desktop App).\n"
                        f"  4. Download JSON and place it at: {secrets_path.resolve()}\n\n"
                        "Tip: You can run the pipeline with `--record-only` or `--dry-run` without credentials!"
                    )
                    logger.error(err_msg)
                    raise FileNotFoundError(err_msg)

                logger.info("Opening browser window for one-time YouTube OAuth authorization...")
                flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
                
                # Check if credentials are for a Web application (requires fixed port like 8080)
                # versus Desktop app (works with any port)
                try:
                    creds = flow.run_local_server(port=8080)
                except Exception as ex:
                    logger.warning(f"OAuth on port 8080 failed: {ex}. Retrying with dynamic port...")
                    creds = flow.run_local_server(port=0)

            # Save refreshed/new token for future unattended runs
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            logger.info(f"Saved OAuth credentials to: {token_path.resolve()}")

        self.youtube = build("youtube", "v3", credentials=creds)
        return self.youtube

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
        """Upload video file to YouTube with metadata and progress reporting."""
        v_path = Path(video_path)
        if not v_path.is_file():
            raise FileNotFoundError(f"Video file to upload does not exist: {v_path.resolve()}")

        if not self.youtube:
            self.authenticate()

        logger.info(f"Preparing YouTube upload for: {v_path.name} ({v_path.stat().st_size / (1024*1024):.2f} MB)")
        logger.info(f"Title: {title}")
        effective_privacy = "private" if publish_at else privacy_status
        logger.info(f"Privacy: {effective_privacy} | Category: {category_id}")
        if publish_at:
            logger.info(f"Scheduled Release: {publish_at}")

        status_body = {
            "privacyStatus": effective_privacy,
            "selfDeclaredMadeForKids": made_for_kids
        }
        if publish_at:
            status_body["publishAt"] = publish_at

        body = {
            "snippet": {
                "title": title[:100],  # YouTube max title length is 100
                "description": description[:5000],
                "tags": tags or self.config.tags,
                "categoryId": category_id
            },
            "status": status_body
        }

        # Resumable media upload in 5MB chunks
        media = MediaFileUpload(
            str(v_path),
            chunksize=5 * 1024 * 1024,
            resumable=True
        )

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        logger.info("Starting chunked upload to YouTube...")
        response = None
        retry_count = 0
        max_retries = 5

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    logger.info(f"YouTube Upload Progress: {pct}% complete")
            except HttpError as ex:
                if ex.resp.status in [500, 502, 503, 504] and retry_count < max_retries:
                    retry_count += 1
                    sleep_secs = 2 ** retry_count
                    logger.warning(f"Transient HTTP {ex.resp.status}. Retrying in {sleep_secs}s...")
                    time.sleep(sleep_secs)
                else:
                    logger.error(f"YouTube upload failed with HTTP error: {ex}")
                    raise
            except Exception as ex:
                if retry_count < max_retries:
                    retry_count += 1
                    sleep_secs = 2 ** retry_count
                    logger.warning(f"Upload connection error: {ex}. Retrying in {sleep_secs}s...")
                    time.sleep(sleep_secs)
                else:
                    logger.error(f"Upload aborted after {max_retries} retries: {ex}")
                    raise

        video_id = response.get("id")
        video_url = f"https://youtu.be/{video_id}"
        logger.info(f"[SUCCESS] Video successfully uploaded to YouTube!")
        logger.info(f"Video URL: {video_url}")

        # Optional thumbnail upload
        if thumbnail_path and Path(thumbnail_path).is_file():
            self._set_thumbnail(video_id, thumbnail_path)

        return video_url

    def _set_thumbnail(self, video_id: str, thumbnail_path: str) -> None:
        """Upload custom thumbnail for video."""
        logger.info(f"Setting custom thumbnail: {thumbnail_path}...")
        try:
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            logger.info("[SUCCESS] Thumbnail uploaded.")
        except Exception as e:
            logger.warning(f"Could not upload thumbnail: {e}")
