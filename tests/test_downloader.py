"""Tests for the downloader module."""
import pytest

from kidstunes.config import Config
from kidstunes.downloader import Downloader


class TestDownloader:
    """Test cases for the Downloader class."""

    @pytest.fixture
    def config(self, tmp_path):
        """Create a test config."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
discord:
  token: "test_token"
  request_channel_id: 123
  approval_channel_id: 456
  admin_role_id: 789

paths:
  output_dir: "/tmp/test_music"
  database: ":memory:"
  temp_dir: "/tmp"

ytdlp:
  audio_format: "mp3"
  audio_quality: "192"
  search_prefix: "ytsearch1:"

xai:
  api_key: ""
  model: "test-model"
"""
        )
        return Config(str(config_file))

    @pytest.fixture
    def downloader(self, config):
        """Create a test downloader."""
        return Downloader(None, config)

    def test_sanitize_filename(self, downloader):
        """Test filename sanitization."""
        assert downloader.sanitize_filename("test.mp3") == "test.mp3"
        assert downloader.sanitize_filename("test<file>.mp3") == "test_file_.mp3"
        assert (
            downloader.sanitize_filename("for KING + COUNTRY") == "for KING _ COUNTRY"
        )

    @pytest.mark.asyncio
    async def test_refine_search_no_api_key(self, downloader):
        """Test search refinement without API key."""
        result = await downloader.refine_search("test query")
        assert result == "test query"
