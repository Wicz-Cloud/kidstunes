import asyncio
import re
from pathlib import Path
from typing import Any, Optional, cast

import requests
import yt_dlp

from .config import Config
from .database import Database


class Downloader:
    def __init__(self, db: Database, config: Config) -> None:
        self.db = db
        self.config = config

    def sanitize_filename(self, name: str) -> str:
        """Sanitize filename/directory name to avoid issues with special characters."""
        # Replace invalid characters with underscores
        return re.sub(r'[<>:"/\\|?*+]', "_", name).strip()

    async def refine_search(self, user_query: str) -> str:
        """Legacy method for backward compatibility."""
        result = await self.refine_search_structured(user_query)
        return result.get("refined_search_term") or user_query

    async def refine_search_structured(
        self, user_query: str
    ) -> dict[str, Optional[str]]:
        """Extract artist, song, and album information from user query using AI."""
        if not self.config.xai_api_key:
            return {
                "refined_search_term": user_query,
                "artist": None,
                "song": None,
                "album": None,
            }

        prompt = f"""Given this music request: "{user_query}"

Extract the artist name, song title, and album name (if mentioned) from the request.
Format your response as a JSON object with these exact keys:
- "artist": the artist/band name (or null if not identifiable)
- "song": the song title (or null if not identifiable)
- "album": the album name (or null if not mentioned)
- "refined_search_term": an optimized YouTube search query for finding the official music video

Examples:
Input: "drummer boy king and country"
Output: {{"artist": "for KING + COUNTRY", "song": "Little Drummer Boy", "album": null, "refined_search_term": "for KING + COUNTRY Little Drummer Boy Official Music Video"}}

Input: "taylor swift blank space"
Output: {{"artist": "Taylor Swift", "song": "Blank Space", "album": null, "refined_search_term": "Taylor Swift Blank Space Official Music Video"}}

Input: "bohemian rhapsody queen"
Output: {{"artist": "Queen", "song": "Bohemian Rhapsody", "album": null, "refined_search_term": "Queen Bohemian Rhapsody Official Music Video"}}

Return only the JSON object, no extra text."""

        try:
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.config.xai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.config.xai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.1,
                },
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()

            # Try to parse JSON response
            try:
                import json

                parsed = json.loads(content)
                # Validate required keys and return proper types
                return {
                    "artist": parsed.get("artist"),
                    "song": parsed.get("song"),
                    "album": parsed.get("album"),
                    "refined_search_term": parsed.get("refined_search_term")
                    or user_query,
                }
            except (json.JSONDecodeError, ValueError, KeyError):
                # Fallback: extract what we can from the text
                print(f"Failed to parse AI response as JSON: {content}")
                return {
                    "refined_search_term": content if content else user_query,
                    "artist": None,
                    "song": None,
                    "album": None,
                }
        except Exception as e:
            print(f"AI refinement failed: {e}")
            return {
                "refined_search_term": user_query,
                "artist": None,
                "song": None,
                "album": None,
            }

    async def search_and_download(
        self,
        request_id: int,
        search_term: str,
        artist: Optional[str] = None,
        song: Optional[str] = None,
        album: Optional[str] = None,
    ) -> str:
        print(f"Searching for: {search_term}")

        # Use AI-identified metadata if available
        target_artist = artist or "Unknown Artist"
        target_album = album or "Singles"
        target_song = song or "Unknown Song"

        # Sanitize names for filesystem
        sanitized_artist = self.sanitize_filename(target_artist)
        sanitized_album = self.sanitize_filename(target_album)

        # Search for the video
        search_opts = {
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            result = ydl.extract_info(
                f"{self.config.search_prefix}{search_term}", download=False
            )
            if "entries" not in result or not result["entries"]:
                raise Exception("No search results found")
            video = result["entries"][0]
            url = video["webpage_url"]
            title = video["title"]

        # Update DB with URL and title
        await self.db.update_request(
            request_id, youtube_url=url, youtube_title=title, status="downloading"
        )

        # Create proper directory structure using AI metadata
        output_path = self.config.output_dir
        artist_dir = Path(output_path) / sanitized_artist
        album_dir = artist_dir / sanitized_album
        album_dir.mkdir(parents=True, exist_ok=True)

        # Set up yt-dlp options with proper metadata
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.config.audio_format,
                    "preferredquality": self.config.audio_quality,
                }
            ],
            "outtmpl": str(
                album_dir / f"{self.sanitize_filename(target_song)}.%(ext)s"
            ),
            "writethumbnail": True,
            "embedthumbnail": True,
            "add_metadata": True,
            "quiet": True,
            "no_warnings": True,
            "clean_infojson": True,  # Remove info json after download
            "rm_cache_dir": True,  # Clean up cache
        }

        # Add metadata override - always set what we have, using defaults for missing values
        ydl_opts["artist"] = target_artist
        ydl_opts["title"] = target_song
        ydl_opts["album"] = target_album

        # Run download in thread to avoid blocking
        try:
            info = await asyncio.to_thread(self._download_sync, url, ydl_opts)
        except Exception as e:
            # Clean up any partial files on failure
            expected_path = (
                album_dir
                / f"{self.sanitize_filename(target_song)}.{self.config.audio_format}"
            )
            if expected_path.exists():
                try:
                    expected_path.unlink()
                    print(f"Cleaned up partial file: {expected_path}")
                except Exception as cleanup_error:
                    print(
                        f"Failed to clean up partial file {expected_path}: {cleanup_error}"
                    )
            raise e

        # Get actual file path
        file_path = cast(str, info.get("filepath"))
        if not file_path:
            # Fallback to constructed path
            ext = self.config.audio_format
            file_path = str(album_dir / f"{self.sanitize_filename(target_song)}.{ext}")

        # Update DB with file path
        await self.db.update_request(request_id, file_path=file_path, status="complete")

        # Process with beets for metadata cleaning if enabled
        if self.config.beets_enabled:
            try:
                await self._process_with_beets(file_path, request_id)
            except Exception as e:
                print(f"Beets processing failed for {file_path}: {e}")
                # Don't fail the entire process if beets fails

        return file_path

    def _download_sync(self, url: str, ydl_opts: dict) -> Any:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    async def _process_with_beets(self, file_path: str, request_id: int) -> None:
        """Process downloaded file with beets for metadata cleaning and MusicBrainz integration."""
        try:
            import os

            print(f"Processing {file_path} with beets...")

            # Use beets command line interface for simplicity and reliability
            cmd = [
                "beet",
                "import",
                "--quiet",  # Reduce output
                "--timid",  # Don't ask for confirmation
                "--search-id",
                "",  # Don't restrict to specific release
                "--art",  # Fetch album art
                "--noninteractive",  # Never prompt for input
                "--yes",  # Answer yes to all prompts
                file_path,
            ]

            # Set environment variables for beets config
            env = os.environ.copy()
            env["BEETSDIR"] = os.path.dirname(self.config.beets_library_path)

            # Run beets import
            result = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.beets_music_directory,
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                print(f"Beets successfully processed {file_path}")
                # Try to extract metadata from the processed file
                await self._extract_metadata_from_file(file_path, request_id)
            else:
                print(f"Beets processing failed: {stderr.decode()}")

        except FileNotFoundError:
            print("Beets not installed, skipping metadata processing")
        except Exception as e:
            print(f"Beets processing error: {e}")
            # Don't fail the entire process if beets fails

    async def _extract_metadata_from_file(
        self, file_path: str, request_id: int
    ) -> None:
        """Extract metadata from processed file and update database."""
        try:
            import os

            from beets import library

            # Initialize beets library
            lib_path = self.config.beets_library_path
            if os.path.exists(lib_path):
                lib = library.Library(lib_path)

                # Find the item in the library
                query = library.PathQuery("path", file_path)
                items = lib.items(query)

                for item in items:
                    await self.db.update_request(
                        request_id,
                        artist=item.artist if item.artist else None,
                        song=item.title if item.title else None,
                        album=item.album if item.album else None,
                    )
                    print(
                        f"Updated metadata: {item.artist} - {item.title} (album: {item.album})"
                    )
                    break

        except Exception as e:
            print(f"Metadata extraction failed: {e}")
