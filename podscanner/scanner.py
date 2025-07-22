#!/usr/bin/env python3
"""
Main scanner module for detecting and processing podcast sources
"""

import sys
import subprocess
from pathlib import Path

from .extractors import extract_apple_podcast_rss, extract_rss_from_website
from .processors import PodcastDownloader, PodcastTranscriber
from .models import DownloadConfig

class PodScanner:
    """Main scanner class for handling different podcast sources"""
    
    def __init__(self):
        """Initialize the scanner"""
        self.config = DownloadConfig()
    
    def detect_source_type(self, url: str) -> str:
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
    
    def download_youtube_podcast(self, url: str, max_episodes: int = None) -> bool:
        """Download podcast episodes from YouTube using yt-dlp"""
        try:
            print(f"📺 Downloading from YouTube: {url}")
            
            downloads_dir = Path(self.config.download_dir)
            downloads_dir.mkdir(exist_ok=True)
            
            # Build yt-dlp command
            cmd = [
                'yt-dlp',
                '--extract-flat', 'false',
                '--format', 'bestaudio',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',  # Best quality
                '--output', str(downloads_dir / '%(uploader)s_-_%(title)s.%(ext)s'),
                '--embed-metadata',
                '--add-metadata',
                '--write-info-json',
            ]
            
            # Handle playlist limits
            if max_episodes:
                cmd.extend(['--playlist-end', str(max_episodes)])
            
            cmd.append(url)
            
            print(f"🚀 Executing: yt-dlp {url}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            print("✅ YouTube download completed!")
            
            # Optionally trigger transcription
            if self.config.transcribe_enabled:
                print("\n🎙️ Starting transcription...")
                transcriber = PodcastTranscriber(self.config)
                transcriber.transcribe_all_episodes()
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ YouTube download failed: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")
            return False
        except FileNotFoundError:
            print("❌ yt-dlp not found. Please install it:")
            print("   pip install yt-dlp")
            return False

    def get_spotify_info(self, url: str) -> None:
        """Get information about Spotify podcast (limited support)"""
        print("🎵 Spotify podcast detected...")
        print("⚠️  Note: Spotify podcasts are often exclusive and may not have RSS feeds")
        print("💡 Try searching for the same podcast on other platforms:")
        print("   • Apple Podcasts")
        print("   • Google Podcasts") 
        print("   • The podcast's official website")
    
    def scan_and_download(self, url: str, max_episodes: int = None) -> None:
        """Main method to scan URL and download podcast content"""
        print("🎧 podScanner")
        print("=" * 50)
        
        # Detect source type
        source_type = self.detect_source_type(url)
        print(f"🔍 Detected source type: {source_type}")
        
        if source_type == 'apple_podcasts':
            print("🍎 Processing Apple Podcasts URL...")
            rss_url = extract_apple_podcast_rss(url)
            if rss_url:
                print(f"✅ Found RSS feed: {rss_url}")
                self._process_rss_feed(rss_url, max_episodes)
            else:
                print("❌ Could not extract RSS feed from Apple Podcasts")
        
        elif source_type == 'youtube':
            print("📺 Processing YouTube URL...")
            self.download_youtube_podcast(url, max_episodes)
            
        elif source_type == 'spotify':
            self.get_spotify_info(url)
            
        elif source_type == 'rss':
            print("📡 Processing RSS feed...")
            self._process_rss_feed(url, max_episodes)
            
        elif source_type == 'unknown':
            print("🌐 Unknown source, searching for RSS feeds...")
            rss_url = extract_rss_from_website(url)
            if rss_url:
                print(f"✅ Found RSS feed: {rss_url}")
                self._process_rss_feed(rss_url, max_episodes)
            else:
                print("❌ No RSS feed found.")
                print("\n💡 Alternative approaches:")
                print("1. Check if the podcast is available on Apple Podcasts or YouTube")
                print("2. Look for RSS/feed links on the website manually")
                print("3. Contact the podcast creator for RSS feed information")
        
        print("\n🎉 Processing complete!")
    
    def _process_rss_feed(self, rss_url: str, max_episodes: int = None) -> None:
        """Process an RSS feed using the modular components"""
        # Download episodes
        downloader = PodcastDownloader(self.config)
        episodes = downloader.parse_episodes_from_feed(rss_url, max_episodes)
        
        if not episodes:
            print("❌ No episodes found in the RSS feed")
            return
        
        downloaded_count = downloader.download_episodes(episodes)
        
        # Transcribe if enabled
        if self.config.transcribe_enabled and downloaded_count > 0:
            print("\n🎙️ Starting transcription...")
            transcriber = PodcastTranscriber(self.config)
            transcriber.transcribe_episodes(episodes)