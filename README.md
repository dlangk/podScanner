# podScanner

Download podcasts from multiple sources, and transcribe them using OpenAI's Whisper.

## Prerequisites

- **Python 3.12** or higher
- **ffmpeg**: `brew install ffmpeg`
- ~1GB free space for Whisper model (downloaded on first run)

## Setup

```bash
# Create virtual environment (first time only)
python3.12 -m venv venv

# Activate virtual environment (every time)
source venv/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Run the program (every time)
# Format: python main.py <URL> [max_episodes]
python main.py "https://podcasts.apple.com/us/podcast/the-daily/id1200361736" 5
python main.py "https://youtube.com/playlist?list=..." 10
python main.py "https://feeds.npr.org/510289/podcast.xml" 3

**Alternative:** Direct execution without activation
```bash
./venv/bin/python main.py <URL> [max_episodes]
```

## Supported Sources
- 🍎 **Apple Podcasts** - Automatically extracts RSS feeds  
- 📺 **YouTube** - Channels, playlists, individual videos
- 📡 **RSS Feeds** - Direct podcast feeds
- 🌐 **Websites** - Searches for RSS feeds automatically

## Tools
1. **`main.py`** - Universal downloader (main entry point)
2. **`podcast_downloader.py`** - Direct RSS downloader with transcription
3. **`apple_podcast_extractor.py`** - Standalone RSS extractor

## Output
- Audio files: `downloads/` directory
- Transcripts: `transcripts/` directory

## Dependencies
- `requests`, `feedparser`, `openai-whisper`, `torch`, `torchaudio`, `yt-dlp`, `psutil`
- All listed in `requirements.txt`