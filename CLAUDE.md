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

# Direct RSS downloader with transcription
python podcast_downloader.py

# Standalone RSS extractor
python apple_podcast_extractor.py
```

## Architecture Overview

### Core Components

1. **`main.py`** - Entry point and lightweight orchestrator that routes requests to appropriate handlers
2. **`pod_scanner.py`** - Main scanner class (`PodScanner`) that detects source types and coordinates processing
3. **`models.py`** - Data classes: `EpisodeInfo`, `DownloadConfig`, `ProcessingStats`
4. **`extractors.py`** - RSS feed extraction from various sources (Apple Podcasts, web scraping)
5. **`downloader.py`** - `PodcastDownloader` class handles RSS parsing and episode downloading
6. **`transcriber.py`** - `PodcastTranscriber` class manages parallel transcription with CPU optimization
7. **`utils.py`** - Utility functions for file operations, sanitization, metadata handling

### Processing Flow

1. **URL Detection**: `PodScanner.detect_source_type()` identifies the podcast source
2. **RSS Extraction**: For Apple Podcasts/websites, extract RSS feed URLs using iTunes API or web scraping
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