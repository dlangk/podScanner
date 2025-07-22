#!/usr/bin/env python3
"""
RSS Feed Extractors

Extract RSS feed URLs from various podcast sources.
"""

import requests
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

def extract_rss_from_apple_podcasts(apple_url: str) -> Optional[str]:
    """Extract RSS feed URL from Apple Podcasts URL"""
    try:
        print(f"🍎 Extracting RSS from Apple Podcasts URL: {apple_url}")
        
        # Extract podcast ID from URL
        id_match = re.search(r'/id(\d+)', apple_url)
        if not id_match:
            print("❌ Could not extract podcast ID from URL")
            return None
        
        podcast_id = id_match.group(1)
        print(f"📱 Found podcast ID: {podcast_id}")
        
        # Use iTunes Search API to get RSS feed
        search_url = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast"
        
        response = requests.get(search_url)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('results'):
            print("❌ No results found from iTunes API")
            return None
        
        podcast_info = data['results'][0]
        rss_url = podcast_info.get('feedUrl')
        
        if not rss_url:
            print("❌ No RSS feed found in podcast data")
            return None
        
        print(f"✅ Found RSS feed: {rss_url}")
        print(f"📋 Podcast: {podcast_info.get('collectionName', 'Unknown')}")
        print(f"👨‍🎤 Artist: {podcast_info.get('artistName', 'Unknown')}")
        
        return rss_url
        
    except Exception as e:
        print(f"❌ Error extracting RSS feed: {e}")
        return None

def extract_rss_from_webpage(url: str) -> Optional[str]:
    """Try to find RSS feed links in webpage HTML"""
    try:
        print(f"🔍 Searching for RSS feeds in webpage: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        html = response.text
        
        # Look for RSS feed links
        rss_patterns = [
            r'<link[^>]*type=["\']application/rss\+xml["\'][^>]*href=["\']([^"\']+)["\']',
            r'<link[^>]*href=["\']([^"\']+)["\'][^>]*type=["\']application/rss\+xml["\']',
            r'href=["\']([^"\']*\.rss)["\']',
            r'href=["\']([^"\']*feed[^"\']*)["\']'
        ]
        
        rss_feeds = []
        for pattern in rss_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            rss_feeds.extend(matches)
        
        # Remove duplicates and filter valid URLs
        unique_feeds = list(set(rss_feeds))
        valid_feeds = [feed for feed in unique_feeds if feed.startswith(('http', '//'))]
        
        if valid_feeds:
            print(f"✅ Found {len(valid_feeds)} potential RSS feed(s):")
            for i, feed in enumerate(valid_feeds, 1):
                print(f"   {i}. {feed}")
            return valid_feeds[0]  # Return the first one
        else:
            print("❌ No RSS feeds found in webpage")
            return None
            
    except Exception as e:
        print(f"❌ Error searching webpage: {e}")
        return None

def check_dependencies() -> List[str]:
    """Check if required dependencies are available"""
    missing = []
    
    # Check for yt-dlp
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        missing.append('yt-dlp')
    
    return missing

def install_yt_dlp() -> bool:
    """Install yt-dlp using pip"""
    try:
        print("📦 Installing yt-dlp...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'yt-dlp'])
        print("✅ yt-dlp installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install yt-dlp")
        return False

def download_youtube_podcast(url: str, max_episodes: Optional[int] = None, audio_format: str = 'mp3') -> bool:
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

def get_spotify_info(url: str) -> None:
    """Get information about Spotify podcast (limited support)"""
    print("🎵 Spotify podcasts detected...")
    print("⚠️  Note: Spotify podcasts are often exclusive and may not have RSS feeds")
    print("💡 Try searching for the same podcast on other platforms:")
    print("   • Apple Podcasts")
    print("   • Google Podcasts") 
    print("   • The podcast's official website") 