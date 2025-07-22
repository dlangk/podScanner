#!/usr/bin/env python3
"""
Utility Functions for Podcast Downloader

Common helper functions and utilities.
"""

import re
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse

def sanitize_filename(filename: str) -> str:
    """Remove or replace characters that aren't valid in filenames"""
    # Remove HTML tags
    filename = re.sub(r'<[^>]+>', '', filename)
    # Replace invalid characters with underscores
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove multiple spaces and replace with single underscore
    filename = re.sub(r'\s+', '_', filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename.strip('_')

def get_episode_id(episode: Dict[str, Any], audio_url: str) -> str:
    """Generate a unique ID for an episode based on URL and title"""
    # Use URL as primary identifier, fallback to title hash
    if audio_url:
        return hashlib.md5(audio_url.encode()).hexdigest()
    else:
        title = episode.get('title', '')
        published = episode.get('published', '')
        return hashlib.md5(f"{title}{published}".encode()).hexdigest()

def get_file_extension_from_url(url: str) -> str:
    """Extract file extension from URL, default to .mp3"""
    parsed_url = urlparse(url)
    ext = Path(parsed_url.path).suffix
    return ext if ext else '.mp3'

def load_json_file(filepath: Path) -> Dict[str, Any]:
    """Load JSON file with error handling"""
    if not filepath.exists():
        return {}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load {filepath}: {e}")
        return {}

def save_json_file(filepath: Path, data: Dict[str, Any]) -> bool:
    """Save data to JSON file with error handling"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Warning: Could not save {filepath}: {e}")
        return False

def create_episode_metadata(episode_info, episode_id: str) -> Dict[str, Any]:
    """Create metadata dict for processed episode"""
    return {
        'title': episode_info.get('title', 'Unknown'),
        'published': episode_info.get('published', 'Unknown'), 
        'audio_url': episode_info.get('audio_url', ''),
        'processed_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'audio_file': episode_info.get('audio_file', ''),
        'transcript_file': episode_info.get('transcript_file', '')
    }

def detect_source_type(url: str) -> str:
    """Detect what type of podcast source this is"""
    url_lower = url.lower()
    
    if 'podcasts.apple.com' in url_lower:
        return 'apple_podcasts'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'spotify.com' in url_lower:
        return 'spotify'
    elif url_lower.endswith('.rss') or 'feed' in url_lower or 'rss' in url_lower:
        return 'rss'
    else:
        return 'unknown'

def format_time_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def print_stats_summary(stats, title: str = "Processing Summary"):
    """Print formatted statistics summary"""
    print(f"\n📊 {title}:")
    if hasattr(stats, 'total_episodes'):
        print(f"   • Total episodes found: {stats.total_episodes}")
    if hasattr(stats, 'downloaded'):
        print(f"   • Downloaded: {stats.downloaded}")
    if hasattr(stats, 'skipped'):
        print(f"   • Skipped (already done): {stats.skipped}")
    if hasattr(stats, 'failed'):
        print(f"   • Failed: {stats.failed}")
    if hasattr(stats, 'transcribed'):
        print(f"   • Transcribed: {stats.transcribed}")
    if hasattr(stats, 'already_transcribed'):
        print(f"   • Already transcribed: {stats.already_transcribed}") 