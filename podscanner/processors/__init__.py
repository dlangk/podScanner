"""
Processors for downloading and transcribing podcasts
"""

from .downloader import PodcastDownloader
from .transcriber import PodcastTranscriber

__all__ = ['PodcastDownloader', 'PodcastTranscriber']