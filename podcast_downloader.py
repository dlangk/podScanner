#!/usr/bin/env python3
"""
Simple Podcast Downloader and Transcriber

This script downloads podcast episodes from RSS feeds and transcribes them.
Audio files are stored in 'downloads/' and transcripts in 'transcripts/'.
"""

import os
import sys
import requests
import feedparser
import whisper
import json
import hashlib
from pathlib import Path
from urllib.parse import urlparse
import re
import time

class PodcastDownloader:
    def __init__(self, downloads_dir="downloads", transcripts_dir="transcripts"):
        self.downloads_dir = Path(downloads_dir)
        self.transcripts_dir = Path(transcripts_dir)
        self.processed_episodes_file = Path("processed_episodes.json")
        
        # Create directories if they don't exist
        self.downloads_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)
        
        # Load processed episodes tracking
        self.processed_episodes = self.load_processed_episodes()
        
        # Load Whisper model
        print("Loading Whisper model...")
        self.whisper_model = whisper.load_model("base")
        print("Whisper model loaded!")
    
    def load_processed_episodes(self):
        """Load the list of already processed episodes"""
        if self.processed_episodes_file.exists():
            try:
                with open(self.processed_episodes_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load processed episodes file: {e}")
                return {}
        return {}
    
    def save_processed_episodes(self):
        """Save the list of processed episodes"""
        try:
            with open(self.processed_episodes_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_episodes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save processed episodes file: {e}")
    
    def get_episode_id(self, episode, audio_url):
        """Generate a unique ID for an episode based on URL and title"""
        # Use URL as primary identifier, fallback to title hash
        if audio_url:
            return hashlib.md5(audio_url.encode()).hexdigest()
        else:
            title = episode.get('title', '')
            published = episode.get('published', '')
            return hashlib.md5(f"{title}{published}".encode()).hexdigest()
    
    def is_episode_processed(self, episode_id):
        """Check if an episode has already been processed"""
        return episode_id in self.processed_episodes
    
    def mark_episode_processed(self, episode_id, episode_info):
        """Mark an episode as processed"""
        self.processed_episodes[episode_id] = {
            'title': episode_info.get('title', 'Unknown'),
            'published': episode_info.get('published', 'Unknown'),
            'audio_url': episode_info.get('audio_url', ''),
            'processed_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'audio_file': episode_info.get('audio_file', ''),
            'transcript_file': episode_info.get('transcript_file', '')
        }
        self.save_processed_episodes()

    def sanitize_filename(self, filename):
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
    
    def download_file(self, url, filepath):
        """Download a file from URL to filepath with progress indicator"""
        try:
            print(f"Downloading: {filepath.name}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgress: {percent:.1f}%", end='', flush=True)
            
            print(f"\nDownloaded: {filepath}")
            return True
            
        except Exception as e:
            print(f"\nError downloading {url}: {e}")
            return False
    
    def transcribe_audio(self, audio_path):
        """Transcribe audio file using Whisper"""
        try:
            print(f"Transcribing: {audio_path.name}")
            result = self.whisper_model.transcribe(str(audio_path))
            return result["text"]
        except Exception as e:
            print(f"Error transcribing {audio_path}: {e}")
            return None
    
    def process_podcast_feed(self, rss_url, max_episodes=None):
        """Download and transcribe episodes from a podcast RSS feed"""
        try:
            print(f"Parsing RSS feed: {rss_url}")
            feed = feedparser.parse(rss_url)
            
            if feed.bozo:
                print("Warning: RSS feed has parsing issues")
            
            if not hasattr(feed, 'entries') or not feed.entries:
                print("No episodes found in feed")
                return
            
            print(f"Found {len(feed.entries)} episodes")
            
            # Limit episodes if specified
            episodes = feed.entries[:max_episodes] if max_episodes else feed.entries
            processed_count = 0
            skipped_count = 0
            
            for i, episode in enumerate(episodes, 1):
                print(f"\n--- Processing Episode {i}/{len(episodes)} ---")
                print(f"Title: {episode.get('title', 'No title')}")
                
                # Find audio URL
                audio_url = None
                for link in episode.get('links', []):
                    if 'audio' in link.get('type', '').lower():
                        audio_url = link.get('href')
                        break
                
                # Fallback: check enclosures
                if not audio_url and hasattr(episode, 'enclosures'):
                    for enclosure in episode.enclosures:
                        if 'audio' in enclosure.get('type', '').lower():
                            audio_url = enclosure.get('href')
                            break
                
                if not audio_url:
                    print("No audio URL found for this episode, skipping...")
                    continue
                
                # Check if episode is already processed
                episode_id = self.get_episode_id(episode, audio_url)
                if self.is_episode_processed(episode_id):
                    print(f"✅ Episode already processed (ID: {episode_id[:8]}...), skipping...")
                    skipped_count += 1
                    continue
                
                # Create filename
                title = episode.get('title', f'episode_{i}')
                safe_title = self.sanitize_filename(title)
                
                # Get file extension from URL
                parsed_url = urlparse(audio_url)
                ext = os.path.splitext(parsed_url.path)[1] or '.mp3'
                
                audio_filename = f"{safe_title}{ext}"
                audio_path = self.downloads_dir / audio_filename
                transcript_path = self.transcripts_dir / f"{safe_title}.txt"
                
                # Download audio file if not exists
                audio_downloaded = False
                if audio_path.exists():
                    print(f"Audio file already exists: {audio_path}")
                    audio_downloaded = True
                else:
                    # Download audio file
                    if self.download_file(audio_url, audio_path):
                        audio_downloaded = True
                
                if not audio_downloaded:
                    print("Failed to download audio, skipping transcription...")
                    continue
                
                # Transcribe audio if not exists
                transcript_created = False
                if transcript_path.exists():
                    print(f"Transcript already exists: {transcript_path}")
                    transcript_created = True
                else:
                    transcript = self.transcribe_audio(audio_path)
                    if transcript:
                        with open(transcript_path, 'w', encoding='utf-8') as f:
                            f.write(f"Title: {episode.get('title', 'No title')}\n")
                            f.write(f"URL: {audio_url}\n")
                            f.write(f"Published: {episode.get('published', 'Unknown')}\n")
                            f.write(f"Episode ID: {episode_id}\n")
                            f.write(f"\n--- TRANSCRIPT ---\n\n")
                            f.write(transcript)
                        print(f"Transcript saved: {transcript_path}")
                        transcript_created = True
                    else:
                        print("Failed to transcribe audio")
                
                # Mark episode as processed
                if audio_downloaded or transcript_created:
                    episode_info = {
                        'title': episode.get('title', 'No title'),
                        'published': episode.get('published', 'Unknown'),
                        'audio_url': audio_url,
                        'audio_file': str(audio_path.name),
                        'transcript_file': str(transcript_path.name) if transcript_created else ''
                    }
                    self.mark_episode_processed(episode_id, episode_info)
                    processed_count += 1
                    print(f"✅ Episode marked as processed (ID: {episode_id[:8]}...)")
                
                # Add a small delay to be respectful to servers
                time.sleep(1)
            
            print(f"\n🎯 Processing Summary:")
            print(f"   • Processed: {processed_count} episodes")
            print(f"   • Skipped (already done): {skipped_count} episodes")
            print(f"   • Total episodes found: {len(episodes)}")
                
        except Exception as e:
            print(f"Error processing feed: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python podcast_downloader.py <RSS_URL> [max_episodes]")
        print("Example: python podcast_downloader.py https://feeds.npr.org/510289/podcast.xml 5")
        sys.exit(1)
    
    rss_url = sys.argv[1]
    max_episodes = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    downloader = PodcastDownloader()
    downloader.process_podcast_feed(rss_url, max_episodes)
    
    print("\n✅ Processing complete!")
    print(f"Audio files saved in: {downloader.downloads_dir}")
    print(f"Transcripts saved in: {downloader.transcripts_dir}")

if __name__ == "__main__":
    main() 