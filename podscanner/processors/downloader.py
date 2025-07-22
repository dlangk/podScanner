#!/usr/bin/env python3
"""
Podcast Downloader Module

Handles RSS feed parsing and episode downloading.
"""

import requests
import feedparser
import time
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from ..models import EpisodeInfo, DownloadConfig, ProcessingStats
from ..utils import sanitize_filename, get_episode_id, get_file_extension_from_url, load_json_file, save_json_file, create_episode_metadata, download_file

class PodcastDownloader:
    """Handles RSS feed parsing and episode downloading"""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.processed_episodes_file = Path("processed_episodes.json")
        self.processed_episodes = load_json_file(self.processed_episodes_file)
    
    def is_episode_processed(self, episode_id: str) -> bool:
        """Check if an episode has already been processed"""
        return episode_id in self.processed_episodes
    
    def mark_episode_processed(self, episode_id: str, episode_info: dict):
        """Mark an episode as processed"""
        self.processed_episodes[episode_id] = create_episode_metadata(episode_info, episode_id)
        save_json_file(self.processed_episodes_file, self.processed_episodes)
    
    def parse_episodes_from_feed(self, rss_url: str) -> List[EpisodeInfo]:
        """Parse RSS feed and return list of episode information"""
        print(f"📡 Parsing RSS feed: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        if feed.bozo:
            print("⚠️  Warning: RSS feed has parsing issues")
        
        if not hasattr(feed, 'entries') or not feed.entries:
            print("❌ No episodes found in feed")
            return []
        
        print(f"📋 Found {len(feed.entries)} episodes")
        
        # Limit episodes if specified
        episodes = feed.entries[:self.config.max_episodes] if self.config.max_episodes else feed.entries
        episode_list = []
        
        for i, episode in enumerate(episodes, 1):
            # Find audio URL
            audio_url = self._find_audio_url(episode)
            
            if not audio_url:
                print(f"⚠️  Episode {i}: No audio URL found, skipping...")
                continue
            
            # Create episode info
            title = episode.get('title', f'episode_{i}')
            safe_title = sanitize_filename(title)
            episode_id = get_episode_id(episode, audio_url)
            
            # Get file extension from URL
            ext = get_file_extension_from_url(audio_url)
            
            audio_filename = f"{safe_title}{ext}"
            audio_path = self.config.downloads_dir / audio_filename
            transcript_path = self.config.transcripts_dir / f"{safe_title}.txt"
            
            episode_info = EpisodeInfo(
                title=title,
                audio_url=audio_url,
                published=episode.get('published', 'Unknown'),
                episode_id=episode_id,
                audio_path=audio_path,
                transcript_path=transcript_path,
                safe_title=safe_title
            )
            
            episode_list.append(episode_info)
        
        return episode_list
    
    def _find_audio_url(self, episode) -> str:
        """Extract audio URL from episode entry"""
        audio_url = None
        
        # Method 1: Check links
        for link in episode.get('links', []):
            if 'audio' in link.get('type', '').lower():
                audio_url = link.get('href')
                break
        
        # Method 2: Check enclosures
        if not audio_url and hasattr(episode, 'enclosures'):
            for enclosure in episode.enclosures:
                if 'audio' in enclosure.get('type', '').lower():
                    audio_url = enclosure.get('href')
                    break
        
        return audio_url
    
    def download_file(self, url: str, filepath: Path) -> bool:
        """Download a file using the utility function"""
        return download_file(url, filepath)
    
    def download_episodes(self, episodes: List[EpisodeInfo]) -> tuple[List[EpisodeInfo], ProcessingStats]:
        """Download all episodes, return list of successfully downloaded episodes and stats"""
        print(f"\n📥 === DOWNLOAD PHASE ===")
        downloaded_episodes = []
        stats = ProcessingStats(total_episodes=len(episodes))
        
        for i, episode in enumerate(episodes, 1):
            print(f"\n📥 Download {i}/{len(episodes)}: {episode.title}")
            
            # Check if already processed
            if self.is_episode_processed(episode.episode_id):
                print(f"✅ Already processed (ID: {episode.episode_id[:8]}...), skipping download")
                stats.skipped += 1
                # Still add to list if audio file exists for potential transcription
                if episode.audio_path.exists():
                    downloaded_episodes.append(episode)
                continue
            
            # Check if audio file already exists
            if episode.audio_path.exists():
                print(f"✅ Audio file already exists: {episode.audio_path.name}")
                downloaded_episodes.append(episode)
                stats.downloaded += 1
                continue
            
            # Download the file
            if self.download_file(episode.audio_url, episode.audio_path):
                downloaded_episodes.append(episode)
                stats.downloaded += 1
            else:
                print(f"❌ Failed to download {episode.title}")
                stats.failed += 1
            
            # Small delay to be respectful to servers
            time.sleep(0.5)
        
        print(f"\n📊 Download Summary:")
        print(f"   • Downloaded: {stats.downloaded} episodes")
        print(f"   • Skipped (already processed): {stats.skipped} episodes")
        print(f"   • Failed: {stats.failed} episodes")
        
        return downloaded_episodes, stats 