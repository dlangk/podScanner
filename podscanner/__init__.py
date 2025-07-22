"""
podscanner - A universal podcast downloader and transcriber

Supports multiple sources including Apple Podcasts, YouTube, RSS feeds, and generic websites.
"""

__version__ = "1.0.0"

from .scanner import PodScanner
from .models import EpisodeInfo, DownloadConfig, ProcessingStats

__all__ = ['PodScanner', 'EpisodeInfo', 'DownloadConfig', 'ProcessingStats']