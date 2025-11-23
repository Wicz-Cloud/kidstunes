from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Request:
    id: Optional[int] = None
    discord_user_id: str = ""
    discord_username: str = ""
    search_term: str = ""
    refined_search_term: Optional[str] = None
    artist: Optional[str] = None
    song: Optional[str] = None
    album: Optional[str] = None
    status: str = "pending"
    message_id: Optional[str] = None  # Approval message ID
    original_message_id: Optional[str] = None  # Original request message ID
    original_channel_id: Optional[str] = None  # Original request channel ID
    youtube_url: Optional[str] = None
    youtube_title: Optional[str] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
