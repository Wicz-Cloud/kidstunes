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
                "album": "Singles",  # Always provide a default album
            }

        prompt = f"""Given this music request: "{user_query}"

Extract the PRIMARY artist name, song title, and album name from the request.
CRITICAL REQUIREMENTS:
- Return only the MAIN/PRIMARY artist name, not featuring artists or collaborations
- ALWAYS identify an album - this is REQUIRED, never return null for album
- Use your knowledge of popular songs to determine the correct album
- CLEAN the song title: remove any YouTube-specific text like "Official Video", "Official Music Video", "(Official Music Video)", "Live", "Lyric Video", "Audio", etc.
- Remove artist name prefixes from song titles (e.g., "Artist - Song Title" should become just "Song Title")
- Remove featuring artists from song titles (e.g., "[feat. Artist]" or "(feat. Artist)" should be removed)
- Remove publisher/record label suffixes from song titles (e.g., "- Label Name" should be removed)
- If the song is a single or you can't identify the album, use "Singles" as the album name

Format your response as a JSON object with these exact keys:
- "artist": the PRIMARY artist/band name only (REQUIRED)
- "song": the CLEAN song title without YouTube extras, artist prefixes, featuring artists, or publisher suffixes (REQUIRED)
- "album": the album name (REQUIRED - never null)
- "refined_search_term": an optimized YouTube search query for finding the official music video

Examples:
Input: "no one like the lord circuit rider music"
Output: {{"artist": "Circuit Rider Music", "song": "No One Like The Lord (We Crown You)", "album": "Sovereign", "refined_search_term": "Circuit Rider Music No One Like The Lord Official Music Video"}}

Input: "katy nichole in jesus name official music video"
Output: {{"artist": "Katy Nichole", "song": "In Jesus Name (God of Possible)", "album": "Jesus Changed My Life", "refined_search_term": "Katy Nichole In Jesus Name Official Music Video"}}

Input: "taylor swift blank space official video"
Output: {{"artist": "Taylor Swift", "song": "Blank Space", "album": "1989", "refined_search_term": "Taylor Swift Blank Space Official Music Video"}}

Input: "bohemian rhapsody queen live"
Output: {{"artist": "Queen", "song": "Bohemian Rhapsody", "album": "A Night at the Opera", "refined_search_term": "Queen Bohemian Rhapsody Official Music Video"}}

Input: "love story taylor swift feat. ed sheeran lyric video"
Output: {{"artist": "Taylor Swift", "song": "Love Story", "album": "Fearless", "refined_search_term": "Taylor Swift Love Story Official Music Video"}}

Input: "drummer boy king and country audio"
Output: {{"artist": "for KING + COUNTRY", "song": "Little Drummer Boy", "album": "A Drummer Boy Christmas", "refined_search_term": "for KING + COUNTRY Little Drummer Boy Official Music Video"}}

Input: "jehovah hillsong chris brown official music video"
Output: {{"artist": "Hillsong", "song": "Jehovah", "album": "There Is More", "refined_search_term": "Hillsong Jehovah Official Music Video"}}

Input: "no fear we the kingdom"
Output: {{"artist": "We The Kingdom", "song": "No Fear", "album": "Holy Water", "refined_search_term": "We The Kingdom No Fear Official Music Video"}}

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
                artist = parsed.get("artist")
                song = parsed.get("song")
                album = parsed.get("album")

                # Ensure album is never None - fallback to "Singles" if AI didn't provide one
                if album is None:
                    album = "Singles"

                return {
                    "artist": artist,
                    "song": song,
                    "album": album,
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
                    "album": "Singles",  # Always provide a default album
                }
        except Exception as e:
            print(f"AI refinement failed: {e}")
            return {
                "refined_search_term": user_query,
                "artist": None,
                "song": None,
                "album": "Singles",  # Always provide a default album
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
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
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

        # Set metadata in the options - this will be used by FFmpegMetadata postprocessor
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
        """Process downloaded file with beets for filename cleaning."""
        try:
            import os

            print(f"Processing {file_path} with beets for filename cleaning...")

            # First, set the metadata on the file using kid3 or similar
            # Then use beets to move/rename the file based on the clean metadata

            # Use beets move command to rename file based on metadata
            # This will rename the file to match the artist/album/song structure
            cmd = [
                "beet",
                "move",
                "--yes",  # Don't prompt for confirmation
                "--quiet",  # Reduce output
                file_path,
            ]

            # Set environment variables for beets config
            env = os.environ.copy()
            env["BEETSDIR"] = os.path.dirname(self.config.beets_library_path)

            # Run beets move
            result = await asyncio.create_subprocess_exec(
                *cmd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.beets_music_directory,
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                print(f"Beets successfully renamed {file_path}")
                # The file has been moved, we need to update the database with the new path
                # For now, we'll keep the original path since beets move might not change it if already correct
            else:
                print(f"Beets move failed: {stderr.decode()}")

        except FileNotFoundError:
            print("Beets not installed, skipping filename processing")
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
