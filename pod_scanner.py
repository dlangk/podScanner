#!/usr/bin/env python3
"""
Pod Scanner Module
Used to download podcasts from multiple sources and then transcribe them. More tokens for your local LLM!

Supported sources:
- RSS feeds (direct)
- Apple Podcasts (extract RSS)
- YouTube channels/playlists
- Spotify (where possible)
- Generic websites (search for RSS)
"""

import sys
import subprocess
import importlib.util
from pathlib import Path

# Import our existing downloader
from podcast_downloader import PodcastDownloader
from apple_podcast_extractor import extract_rss_from_apple_podcasts, extract_rss_from_webpage

class PodScanner:
    """Main scanner class for handling different podcast sources"""
    
    def __init__(self):
        """Initialize the scanner"""
        pass
    
    def detect_source_type(self, url):
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
    
    def download_youtube_podcast(self, url, max_episodes=None, audio_format='mp3'):
        """Download podcast episodes from YouTube using yt-dlp"""
        try:
            print(f"📺 Downloading from YouTube: {url}")
            
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            # Build yt-dlp command
            cmd = [
                'yt-dlp',
                '--extract-flat', 'false',
                '--format', 'bestaudio',
                '--audio-format', audio_format,
                '--audio-quality', '0',  # Best quality
                '--output', str(downloads_dir / '%(uploader)s - %(title)s.%(ext)s'),
                '--embed-metadata',
                '--add-metadata',
                '--write-info-json',
            ]
            
            # Handle playlist limits
            if max_episodes:
                cmd.extend(['--playlist-end', str(max_episodes)])
            
            cmd.append(url)
            
            print(f"🚀 Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True)
            
            print("✅ YouTube download completed!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ YouTube download failed: {e}")
            return False

    def get_spotify_info(self, url):
        """Get information about Spotify podcast (limited support)"""
        print("🎵 Spotify podcasts detected...")
        print("⚠️  Note: Spotify podcasts are often exclusive and may not have RSS feeds")
        print("💡 Try searching for the same podcast on other platforms:")
        print("   • Apple Podcasts")
        print("   • Google Podcasts") 
        print("   • The podcast's official website")
        return None
    
    def scan_and_download(self, url, max_episodes=None):
        """Main method to scan URL and download podcast content"""
        print("🎧 Pod Scanner")
        print("=" * 50)
        
        # Detect source type
        source_type = self.detect_source_type(url)
        print(f"🔍 Detected source type: {source_type}")
        
        if source_type == 'apple_podcasts':
            print("🍎 Processing Apple Podcasts URL...")
            rss_url = extract_rss_from_apple_podcasts(url)
            if rss_url:
                print(f"✅ Found RSS feed, using standard downloader...")
                downloader = PodcastDownloader()
                downloader.process_podcast_feed(rss_url, max_episodes)
            else:
                print("❌ Could not extract RSS feed from Apple Podcasts")
        
        elif source_type == 'youtube':
            print("📺 Processing YouTube URL...")
            if self.download_youtube_podcast(url, max_episodes):
                print("✅ YouTube download completed!")
                print("📁 Audio files saved in: downloads/")
                print("💡 To transcribe, use: python podcast_downloader.py on the RSS of your choice")
            
        elif source_type == 'spotify':
            self.get_spotify_info(url)
            
        elif source_type == 'rss':
            print("📡 Processing RSS feed...")
            downloader = PodcastDownloader()
            downloader.process_podcast_feed(url, max_episodes)
            
        elif source_type == 'unknown':
            print("🌐 Unknown source, searching for RSS feeds...")
            rss_url = extract_rss_from_webpage(url)
            if rss_url:
                print(f"✅ Found RSS feed, using standard downloader...")
                downloader = PodcastDownloader()
                downloader.process_podcast_feed(rss_url, max_episodes)
            else:
                print("❌ No RSS feed found.")
                print("\n💡 Alternative approaches:")
                print("1. Check if the podcast is available on Apple Podcasts or YouTube")
                print("2. Look for RSS/feed links on the website manually")
                print("3. Contact the podcast creator for RSS feed information")
        
        print("\n🎉 Processing complete!") 