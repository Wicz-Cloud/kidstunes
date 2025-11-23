# KidsTunes

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Discord](https://img.shields.io/badge/Discord-Bot-blue)](https://discord.com/)

A Discord-based music acquisition system for Plex that allows family members to request music via Discord with an approval workflow. Features AI-powered search refinement, automatic metadata processing with Beets/MusicBrainz, and seamless Plex integration.

## ✨ Features

- 🤖 **AI-Powered Search**: Uses x.ai Grok to intelligently refine music search queries
- 🎵 **Discord Integration**: Simple `!request` command with admin approval workflow
- 📥 **Automatic Downloads**: yt-dlp integration for high-quality audio extraction
- 🏷️ **Smart Metadata**: Beets integration with MusicBrainz for accurate tagging
- 📁 **Plex Ready**: Proper Artist/Album structure for seamless Plex integration
- 🔄 **Approval Workflow**: Admins approve/reject requests with reactions
- 📊 **Status Tracking**: Real-time status updates on original request messages
- 🛡️ **Robust Error Handling**: Automatic cleanup and recovery from failures
- 🔧 **Systemd Service**: Production-ready deployment with automatic restarts

## 📋 Prerequisites

- Python 3.10+
- Discord bot token
- x.ai API key (optional, for AI search refinement)
- Plex Media Server
- yt-dlp and FFmpeg
- Beets (optional, for advanced metadata processing)

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/woczcloud/kidstunes.git
cd kidstunes
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your Discord token, x.ai API key, and paths
```

### 3. Run

```bash
python3 -m kidstunes.main
```

## ⚙️ Configuration

Edit `config.yaml` with your settings:

### Discord Configuration
```yaml
discord:
  token: "YOUR_DISCORD_BOT_TOKEN"
  request_channel_id: 123456789012345678  # Channel for user requests
  approval_channel_id: 123456789012345678 # Channel for admin approvals
  admin_role_id: 123456789012345678      # Role that can approve/reject
```

### AI & Download Settings
```yaml
xai:
  api_key: "xai-YOUR_API_KEY"  # Get from https://x.ai/api
  model: "grok-4-1-fast-non-reasoning"

ytdlp:
  audio_format: "mp3"
  audio_quality: "192"
  search_prefix: "ytsearch1:"
```

### Paths & Beets
```yaml
paths:
  output_dir: "/var/lib/plexmediaserver/Music"
  database: "/home/bill/music_kids/kidstunes/kidstunes.db"
  temp_dir: "/tmp/kidstunes"

beets:
  enabled: true
  library_path: "/home/bill/music_kids/beets_library.db"
  music_directory: "/var/lib/plexmediaserver/Music"
```

## 🏃‍♂️ Production Deployment

### Systemd Service Setup

1. Create the service file:
```bash
sudo tee /etc/systemd/system/kidstunes.service > /dev/null <<EOF
[Unit]
Description=KidsTunes Discord Music Bot
After=network.target

[Service]
Type=simple
User=bill
Group=bill
WorkingDirectory=/home/bill/music_kids/kidstunes
ExecStart=/bin/bash -c 'cd /home/bill/music_kids && source venv/bin/activate && cd kidstunes && python3 -m kidstunes.main'
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kidstunes
sudo systemctl start kidstunes
sudo systemctl status kidstunes
```

## 💬 Usage

### For Users
Send messages in the request channel:
```
!request <song name or artist>
!request Bohemian Rhapsody Queen
!request jazz music for kids
```

### For Admins
- React with ✅ to approve requests
- React with ❌ to reject requests
- Use `!retry <request_id>` for failed downloads
- Original request messages show approval status

### Commands
- `!request <query>`: Submit a music request
- `!retry <request_id>`: Retry a failed download (admin only)
- `!help`: Show available commands

## 🏗️ Architecture

```
kidstunes/
├── kidstunes/
│   ├── __init__.py
│   ├── main.py          # Application entry point
│   ├── bot.py           # Discord bot & approval workflow
│   ├── downloader.py    # AI search & yt-dlp downloads
│   ├── database.py      # SQLite persistence
│   ├── config.py        # Configuration management
│   └── models.py        # Data structures
├── config.yaml          # Runtime configuration
├── requirements.txt     # Python dependencies
├── pyproject.toml       # Package metadata
└── .pre-commit-config.yaml # Code quality hooks
```

## 🔧 Development

### Setup Development Environment

```bash
git clone https://github.com/woczcloud/kidstunes.git
cd kidstunes
python3 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
```

### Code Quality

```bash
# Format code
black .
isort .

# Type checking
mypy kidstunes/

# Run tests
pytest

# Pre-commit checks
pre-commit run --all-files
```

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**: Check Discord token and channel permissions
2. **Download failures**: Ensure yt-dlp and FFmpeg are installed
3. **AI not working**: Verify x.ai API key and network connectivity
4. **Plex not finding files**: Check directory permissions and Plex library setup
5. **Beets errors**: Ensure Beets is installed and configured

### Logs

```bash
# Systemd logs
sudo journalctl -u kidstunes -f

# Manual run logs
tail -f kidstunes.log
```

### Debug Mode

Set environment variable for verbose logging:
```bash
export KIDSTUNES_DEBUG=1
python3 -m kidstunes.main
```

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube downloading
- [Beets](https://github.com/beetbox/beets) - Music library management
- [x.ai](https://x.ai/) - AI search refinement

### Discord Configuration
- `token`: Your Discord bot token from https://discord.com/developers/applications
- `request_channel_id`: Channel ID where users make requests
- `approval_channel_id`: Channel ID where admins approve requests
- `admin_role_id`: Role ID that can approve/reject requests

### Paths
- `output_dir`: Directory for downloaded music (must be accessible by Plex)
- `database`: Path to SQLite database file

### YouTube Download (yt-dlp)
- `audio_format`: Output format (e.g., "mp3")
- `audio_quality`: Quality setting (e.g., "192")
- `search_prefix`: Search prefix (default: "ytsearch1:")

### AI Search Refinement (x.ai)
- `api_key`: Your x.ai API key (get from https://x.ai/)
- `model`: x.ai model to use (default: "grok-beta")

## Setup

### Discord Bot Setup
1. Create a Discord application at https://discord.com/developers/applications
2. Create a bot user and copy the token
3. Invite the bot to your server with appropriate permissions
4. Get channel IDs and role IDs from Discord (enable Developer Mode)

### Plex Integration
1. Ensure Plex can access the output directory
2. Add the output directory to Plex's Music library
3. The bot downloads to: `/var/lib/plexmediaserver/Music/plex_music`

### Permissions
The output directory must be owned by the `plex` user:
```bash
sudo chown -R plex:plex /var/lib/plexmediaserver/Music/plex_music
```

## Running the Bot

### Manual Run
```bash
cd /path/to/kidstunes
source venv/bin/activate
python3 -m kidstunes.main
```

### As a Systemd Service
1. Create the service file:
   ```bash
   sudo tee /etc/systemd/system/kidstunes.service > /dev/null <<EOF
   [Unit]
   Description=KidsTunes Discord Music Bot
   After=network.target

   [Service]
   Type=simple
   User=bill
   Group=bill
   WorkingDirectory=/home/bill/music_kids/kidstunes
   ExecStart=/bin/bash -c 'cd /home/bill/music_kids && source venv/bin/activate && cd kidstunes && python3 -m kidstunes.main'
   Restart=always
   RestartSec=5
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   EOF
   ```

2. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable kidstunes
   sudo systemctl start kidstunes
   ```

3. Check status:
   ```bash
   sudo systemctl status kidstunes
   ```

4. View logs:
   ```bash
   sudo journalctl -u kidstunes -f
   ```

## Usage

### Making Requests
Users send messages in the request channel:
```
!request <song name or artist>
```

### Approval Process
1. Bot posts an embed in the approval channel with request details
2. Admins react with ✅ to approve or ❌ to reject
3. Approved requests are automatically downloaded
4. Downloaded files appear in Plex library

### Commands
- `!request <query>`: Submit a music request
- `!retry <request_id>`: Retry a failed download (admin only)
- `!help`: Show available commands

## File Structure

```
kidstunes/
├── kidstunes/
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── bot.py           # Discord bot logic
│   ├── downloader.py    # YouTube download and AI refinement
│   ├── database.py      # SQLite database operations
│   ├── config.py        # Configuration loading
│   └── models.py        # Data models
├── config.yaml          # Configuration file
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Troubleshooting

### Common Issues

1. **Bot not responding**: Check Discord token and permissions
2. **Download failures**: Ensure yt-dlp and FFmpeg are installed
3. **Plex not finding files**: Check permissions and library paths
4. **AI refinement not working**: Verify x.ai API key

### Logs
Check logs with:
```bash
sudo journalctl -u kidstunes -f
```

Or for manual runs:
```bash
tail -f kidstunes.log
```

## License

MIT License
