#!/usr/bin/env python3
"""
Data Models for Podcast Downloader

Shared data classes and configuration models.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class EpisodeInfo:
    """Container for episode information"""
    title: str
    audio_url: str
    published: str
    episode_id: str
    audio_path: Path
    transcript_path: Path
    safe_title: str

@dataclass
class DownloadConfig:
    """Configuration for download operations"""
    downloads_dir: Path = Path("downloads")
    transcripts_dir: Path = Path("transcripts")
    max_episodes: Optional[int] = None
    max_workers: Optional[int] = None
    use_multiprocessing: bool = True
    
    def __post_init__(self):
        """Ensure directories exist"""
        self.downloads_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)

@dataclass
class ProcessingStats:
    """Statistics from processing operations"""
    total_episodes: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    transcribed: int = 0
    already_transcribed: int = 0 