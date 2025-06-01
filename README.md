# Podcast Downloader & Transcriber

A simple Python script that downloads podcast episodes from RSS feeds and transcribes them using OpenAI's Whisper.

## Setup

### Prerequisites
- Python 3.12 (already verified on your system)

### Virtual Environment Setup
The virtual environment is already created and configured with all dependencies.

### Activation Options

**Option 1: Use the activation script (MUST use 'source')**
```bash
source activate.sh
```
**⚠️ Important: Don't use `./activate.sh` - it won't work! You must use `source activate.sh`**

**Option 2: Activate manually**
```bash
source venv/bin/activate
```

**Option 3: Run directly with virtual environment Python (no activation needed)**
```bash
./venv/bin/python podcast_downloader.py <RSS_URL> [max_episodes]
```

## Usage

### Basic Usage
```bash
# First, activate the environment
source activate.sh

# Then run the script
python podcast_downloader.py "https://feeds.npr.org/510289/podcast.xml"

# Download and transcribe only the first 5 episodes
python podcast_downloader.py "https://feeds.npr.org/510289/podcast.xml" 5
```

### Alternative: Direct execution (no activation needed)
```bash
# Run directly without activating
./venv/bin/python podcast_downloader.py "https://api.substack.com/feed/podcast/69345.rss" 3
```

### Output
- Audio files are saved in `downloads/` directory
- Transcripts are saved in `transcripts/` directory

## Dependencies

All dependencies are listed in `requirements.txt`:
- `requests` - For downloading files
- `feedparser` - For parsing RSS feeds
- `openai-whisper` - For audio transcription
- `torch` & `torchaudio` - Required by Whisper

## Deactivating Virtual Environment

When you're done working, deactivate the virtual environment:
```bash
deactivate
```

## Features

- Downloads podcast episodes from any RSS feed
- Stores audio files in a `downloads/` directory
- Transcribes audio using OpenAI's Whisper
- Stores transcripts in a `transcripts/` directory
- Progress indicators for downloads
- Smart filename sanitization
- **Enhanced duplicate prevention:**
  - Tracks processed episodes in `processed_episodes.json`
  - Uses URL-based unique episode identification
  - Skips already downloaded/transcribed episodes automatically
  - Shows processing summary with counts
- Git-friendly: Audio files and transcripts are automatically excluded from version control

## Output Files

- **Audio files**: Saved in `downloads/` directory with sanitized filenames
- **Transcripts**: Saved in `transcripts/` directory as `.txt` files  
- **Episode tracking**: `processed_episodes.json` tracks all processed episodes
- Each transcript includes episode metadata (title, URL, publish date, episode ID) and the full transcription

## Duplicate Prevention

The script now includes robust duplicate prevention:

1. **Episode tracking**: Each episode gets a unique ID based on its audio URL
2. **Persistent memory**: Processed episodes are saved in `processed_episodes.json`
3. **Smart skipping**: Re-running the script will automatically skip already processed episodes
4. **File-based backup**: Even if tracking file is lost, existing audio/transcript files prevent re-downloading
5. **Processing summary**: Shows how many episodes were processed vs. skipped

Example output:
```
✅ Episode already processed (ID: a1b2c3d4...), skipping...

🎯 Processing Summary:
   • Processed: 2 episodes
   • Skipped (already done): 3 episodes  
   • Total episodes found: 5
```

## Requirements

- ~1GB free space for Whisper model and episode storage
- Internet connection for downloading episodes

## Notes

- The script uses Whisper's "base" model for transcription (good balance of speed vs accuracy)
- Already downloaded episodes and transcripts are automatically skipped
- Files are saved with sanitized names to avoid filesystem issues
- The script includes a 1-second delay between downloads to be respectful to podcast servers
