# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

podScanner is a Python-based podcast downloader and transcriber that supports multiple sources:
- Apple Podcasts (extracts RSS feeds automatically)
- YouTube channels/playlists 
- Direct RSS feeds
- Generic websites (searches for RSS feeds)
- Limited Spotify support (information only)

The tool downloads audio files and transcribes them using OpenAI's Whisper model for local LLM training data.

## Development Environment

**Python Version**: 3.12 (recommended for best compatibility)

**Setup Commands**:
```bash
# Create virtual environment (first time only)
python3.12 -m venv venv

# Activate virtual environment (every time)
source venv/bin/activate

# Install dependencies (first time only)
pip install -r requirements.txt
```

**Running the Application**:
```bash
# Main entry point - universal downloader
python main.py "<URL>" [max_episodes]

# Examples:
python main.py "https://podcasts.apple.com/us/podcast/the-daily/id1200361736" 5
python main.py "https://youtube.com/playlist?list=..." 10
python main.py "https://feeds.npr.org/510289/podcast.xml" 3

# Alternative: Direct execution without activation
./venv/bin/python main.py <URL> [max_episodes]
```

## Architecture Overview

### Package Structure

```
podscanner/                 # Main package directory
├── __init__.py            # Package initialization
├── scanner.py             # Core scanner logic (PodScanner class)
├── models.py              # Data models (EpisodeInfo, DownloadConfig, ProcessingStats)
├── utils.py               # Utility functions
├── extractors/            # Source-specific extractors
│   ├── __init__.py
│   ├── apple.py          # Apple Podcasts RSS extraction
│   └── rss.py            # Generic website RSS extraction
└── processors/            # Processing components
    ├── __init__.py
    ├── downloader.py      # Episode downloading
    └── transcriber.py     # Audio transcription
```

### Core Components

1. **`main.py`** - CLI entry point that creates PodScanner instance
2. **`podscanner/scanner.py`** - Main scanner class that detects source types and coordinates processing
3. **`podscanner/models.py`** - Data classes for structured data handling
4. **`podscanner/extractors/`** - Modular extractors for different podcast sources
5. **`podscanner/processors/`** - Separate processors for downloading and transcription
6. **`podscanner/utils.py`** - Shared utility functions

### Processing Flow

1. **URL Detection**: `PodScanner.detect_source_type()` identifies the podcast source
2. **RSS Extraction**: Source-specific extractors handle RSS feed discovery
3. **Episode Parsing**: `PodcastDownloader.parse_episodes_from_feed()` parses RSS and creates `EpisodeInfo` objects
4. **Download Phase**: Episodes are downloaded with progress tracking and deduplication
5. **Transcription Phase**: `PodcastTranscriber` handles parallel transcription using Whisper model

### Key Features

- **Multi-source Support**: Apple Podcasts, YouTube, RSS feeds, web scraping
- **Parallel Processing**: CPU-optimized transcription with configurable workers
- **Deduplication**: Episodes tracked in `processed_episodes.json` to avoid reprocessing
- **Progress Tracking**: Real-time download progress and CPU monitoring
- **Flexible Configuration**: `DownloadConfig` for customizing directories, workers, processing mode

### File Structure

- **Audio files**: `downloads/` directory
- **Transcripts**: `transcripts/` directory  
- **Episode tracking**: `processed_episodes.json`
- **Dependencies**: Listed in `requirements.txt`

### YouTube Support

YouTube downloads use `yt-dlp` with specific configuration:
- Best audio quality extraction
- Metadata embedding
- Playlist support with configurable limits
- JSON info file generation

### Transcription System

The transcription system supports both threading and multiprocessing:
- **CPU Monitoring**: `CPUMonitor` class provides optimal worker recommendations
- **Whisper Integration**: Uses OpenAI Whisper "base" model
- **Process/Thread Management**: Configurable execution mode via `DownloadConfig.use_multiprocessing`
- **Error Handling**: Robust error handling with detailed logging