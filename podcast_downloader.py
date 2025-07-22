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
import psutil
import multiprocessing
from pathlib import Path
from urllib.parse import urlparse
import re
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional
import threading
import tqdm

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

class CustomProgressBar:
    """Custom progress bar for thread-safe transcription progress"""
    
    def __init__(self, episode_title, worker_id):
        self.episode_title = episode_title[:30] + "..." if len(episode_title) > 30 else episode_title
        self.worker_id = worker_id
        self.start_time = time.time()
        self.last_update = 0
        
    def update_progress(self, current, total):
        """Update progress and print status"""
        if total == 0:
            return
            
        percent = (current / total) * 100
        elapsed = time.time() - self.start_time
        
        # Only update every 5% to avoid spam
        if percent - self.last_update >= 5:
            remaining = (elapsed / (current / total)) - elapsed if current > 0 else 0
            
            print(f"🎙️  [{self.worker_id}] {self.episode_title}: {percent:.0f}% "
                  f"({current:.0f}/{total:.0f}) [{elapsed:.0f}s elapsed, {remaining:.0f}s remaining]")
            
            self.last_update = percent

# Custom tqdm override for Whisper progress
class WhisperProgressBar(tqdm.tqdm):
    """Custom progress bar that integrates with our progress system"""
    
    def __init__(self, *args, **kwargs):
        # Extract our custom episode info if provided
        self.episode_title = kwargs.pop('episode_title', 'Unknown')
        self.worker_id = kwargs.pop('worker_id', 'Worker')
        super().__init__(*args, **kwargs)
        self.custom_bar = CustomProgressBar(self.episode_title, self.worker_id)
        
    def update(self, n=1):
        super().update(n)
        if self.total:
            self.custom_bar.update_progress(self.n, self.total)

def transcribe_audio_worker_func(episode_info_dict):
    """Standalone worker function for multiprocessing"""
    import whisper
    import json
    import tqdm
    from pathlib import Path
    import os
    import sys
    
    # Reconstruct EpisodeInfo from dict
    episode_info = EpisodeInfo(**episode_info_dict)
    worker_id = f"PID-{os.getpid()}"
    
    try:
        print(f"🎙️  [{worker_id}] Loading Whisper & starting: {episode_info.safe_title}")
        
        # Override tqdm for this process
        original_tqdm = tqdm.tqdm
        
        def custom_tqdm(*args, **kwargs):
            kwargs['episode_title'] = episode_info.title
            kwargs['worker_id'] = worker_id
            kwargs['disable'] = False  # Ensure progress is shown
            return WhisperProgressBar(*args, **kwargs)
        
        # Monkey patch tqdm in whisper's transcribe module
        tqdm.tqdm = custom_tqdm
        whisper.transcribe.tqdm = tqdm  # Make sure whisper uses our tqdm
        
        model = whisper.load_model("base")
        result = model.transcribe(str(episode_info.audio_path), verbose=False)
        transcript = result["text"]
        
        # Restore original tqdm
        tqdm.tqdm = original_tqdm
        
        # Write transcript
        with open(episode_info.transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"Title: {episode_info.title}\n")
            f.write(f"URL: {episode_info.audio_url}\n")
            f.write(f"Published: {episode_info.published}\n")
            f.write(f"Episode ID: {episode_info.episode_id}\n")
            f.write(f"\n--- TRANSCRIPT ---\n\n")
            f.write(transcript)
        
        print(f"✅ [{worker_id}] Completed: {episode_info.safe_title}")
        return episode_info_dict, True
        
    except Exception as e:
        print(f"❌ [{worker_id}] Error transcribing {episode_info.safe_title}: {e}")
        return episode_info_dict, False

class CPUMonitor:
    """Monitor CPU usage and suggest optimal worker count"""
    
    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.monitoring = False
        self.cpu_history = []
        
    def get_optimal_workers(self, current_workers=None):
        """Calculate optimal number of workers based on CPU cores and usage"""
        # Basic calculation: use 75-90% of available cores
        optimal = max(1, int(self.cpu_count * 0.8))
        
        # Cap at reasonable maximum (Whisper models are memory intensive)
        optimal = min(optimal, 8)
        
        print(f"💻 CPU Info:")
        print(f"   • Available cores: {self.cpu_count}")
        print(f"   • Recommended workers: {optimal}")
        
        if current_workers and current_workers != optimal:
            print(f"   • Current workers: {current_workers}")
            if current_workers < optimal:
                print(f"   💡 Consider increasing to {optimal} workers for better CPU utilization")
            elif current_workers > optimal:
                print(f"   ⚠️  {current_workers} workers might cause memory pressure")
        
        return optimal
    
    def start_monitoring(self):
        """Start background CPU monitoring"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop CPU monitoring"""
        self.monitoring = False
        
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            cpu_percent = psutil.cpu_percent(interval=5)
            self.cpu_history.append(cpu_percent)
            
            # Keep only last 10 measurements
            if len(self.cpu_history) > 10:
                self.cpu_history.pop(0)
                
            # Print CPU usage every 30 seconds during transcription
            if len(self.cpu_history) % 6 == 0:  # Every 30 seconds
                avg_cpu = sum(self.cpu_history) / len(self.cpu_history)
                print(f"📊 CPU Usage: {avg_cpu:.1f}% (avg last {len(self.cpu_history)*5}s)")
                
                if avg_cpu < 60:
                    print(f"💡 Low CPU usage - consider increasing workers for better performance")
                elif avg_cpu > 95:
                    print(f"⚠️  High CPU usage - consider reducing workers if system becomes unresponsive")

class PodcastDownloader:
    def __init__(self, downloads_dir="downloads", transcripts_dir="transcripts", max_workers=None, use_multiprocessing=True):
        self.downloads_dir = Path(downloads_dir)
        self.transcripts_dir = Path(transcripts_dir)
        self.processed_episodes_file = Path("processed_episodes.json")
        self.use_multiprocessing = use_multiprocessing
        
        # CPU optimization
        self.cpu_monitor = CPUMonitor()
        
        # Auto-determine optimal workers if not specified
        if max_workers is None:
            self.max_workers = self.cpu_monitor.get_optimal_workers()
        else:
            self.max_workers = max_workers
            self.cpu_monitor.get_optimal_workers(max_workers)
        
        # Create directories if they don't exist
        self.downloads_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)
        
        # Load processed episodes tracking
        self.processed_episodes = self.load_processed_episodes()
        
        # Don't load Whisper model here - load it in transcription workers
        self.whisper_model = None
    
    def load_whisper_model(self):
        """Load Whisper model (called by transcription workers)"""
        if self.whisper_model is None:
            print(f"🎙️  [Worker] Loading Whisper model...")
            self.whisper_model = whisper.load_model("base")
            print(f"🎙️  [Worker] Whisper model loaded!")
        return self.whisper_model
    
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
            print(f"📥 Downloading: {filepath.name}")
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
                            print(f"\r📥 {filepath.name}: {percent:.1f}%", end='', flush=True)
            
            print(f"\n✅ Downloaded: {filepath.name}")
            return True
            
        except Exception as e:
            print(f"\n❌ Error downloading {url}: {e}")
            return False
    
    def transcribe_audio_worker(self, episode_info: EpisodeInfo):
        """Worker function to transcribe a single audio file (ThreadPool version)"""
        worker_id = f"Thread-{threading.get_ident()}"
        
        try:
            # Load Whisper model in this worker
            model = self.load_whisper_model()
            
            print(f"🎙️  [{worker_id}] Starting: {episode_info.safe_title}")
            
            # Override tqdm for this thread
            original_tqdm = tqdm.tqdm
            
            def custom_tqdm(*args, **kwargs):
                kwargs['episode_title'] = episode_info.title
                kwargs['worker_id'] = worker_id
                kwargs['disable'] = False  # Ensure progress is shown
                return WhisperProgressBar(*args, **kwargs)
            
            # Monkey patch tqdm in whisper's transcribe module
            tqdm.tqdm = custom_tqdm
            whisper.transcribe.tqdm = tqdm  # Make sure whisper uses our tqdm
            
            result = model.transcribe(str(episode_info.audio_path), verbose=False)
            transcript = result["text"]
            
            # Restore original tqdm
            tqdm.tqdm = original_tqdm
            
            # Write transcript
            with open(episode_info.transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"Title: {episode_info.title}\n")
                f.write(f"URL: {episode_info.audio_url}\n")
                f.write(f"Published: {episode_info.published}\n")
                f.write(f"Episode ID: {episode_info.episode_id}\n")
                f.write(f"\n--- TRANSCRIPT ---\n\n")
                f.write(transcript)
            
            print(f"✅ [{worker_id}] Completed: {episode_info.safe_title}")
            return episode_info, True
            
        except Exception as e:
            print(f"❌ [{worker_id}] Error transcribing {episode_info.safe_title}: {e}")
            return episode_info, False
    
    def parse_episodes_from_feed(self, rss_url, max_episodes=None) -> List[EpisodeInfo]:
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
        episodes = feed.entries[:max_episodes] if max_episodes else feed.entries
        episode_list = []
        
        for i, episode in enumerate(episodes, 1):
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
                print(f"⚠️  Episode {i}: No audio URL found, skipping...")
                continue
            
            # Create episode info
            title = episode.get('title', f'episode_{i}')
            safe_title = self.sanitize_filename(title)
            episode_id = self.get_episode_id(episode, audio_url)
            
            # Get file extension from URL
            parsed_url = urlparse(audio_url)
            ext = os.path.splitext(parsed_url.path)[1] or '.mp3'
            
            audio_filename = f"{safe_title}{ext}"
            audio_path = self.downloads_dir / audio_filename
            transcript_path = self.transcripts_dir / f"{safe_title}.txt"
            
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
    
    def download_episodes(self, episodes: List[EpisodeInfo]) -> List[EpisodeInfo]:
        """Download all episodes, return list of successfully downloaded episodes"""
        print(f"\n📥 === DOWNLOAD PHASE ===")
        downloaded_episodes = []
        skipped_count = 0
        
        for i, episode in enumerate(episodes, 1):
            print(f"\n📥 Download {i}/{len(episodes)}: {episode.title}")
            
            # Check if already processed
            if self.is_episode_processed(episode.episode_id):
                print(f"✅ Already processed (ID: {episode.episode_id[:8]}...), skipping download")
                skipped_count += 1
                # Still add to list if audio file exists for potential transcription
                if episode.audio_path.exists():
                    downloaded_episodes.append(episode)
                continue
            
            # Check if audio file already exists
            if episode.audio_path.exists():
                print(f"✅ Audio file already exists: {episode.audio_path.name}")
                downloaded_episodes.append(episode)
                continue
            
            # Download the file
            if self.download_file(episode.audio_url, episode.audio_path):
                downloaded_episodes.append(episode)
            else:
                print(f"❌ Failed to download {episode.title}")
            
            # Small delay to be respectful to servers
            time.sleep(0.5)
        
        print(f"\n📊 Download Summary:")
        print(f"   • Downloaded: {len(downloaded_episodes)} episodes")
        print(f"   • Skipped (already processed): {skipped_count} episodes")
        print(f"   • Failed: {len(episodes) - len(downloaded_episodes) - skipped_count} episodes")
        
        return downloaded_episodes
    
    def transcribe_episodes(self, episodes: List[EpisodeInfo]) -> int:
        """Transcribe episodes in parallel, return count of successful transcriptions"""
        print(f"\n🎙️  === TRANSCRIPTION PHASE ===")
        
        # Filter episodes that need transcription
        episodes_to_transcribe = []
        already_transcribed = 0
        
        for episode in episodes:
            if episode.transcript_path.exists():
                print(f"✅ Transcript already exists: {episode.safe_title}")
                already_transcribed += 1
            else:
                episodes_to_transcribe.append(episode)
        
        if not episodes_to_transcribe:
            print("🎉 All episodes already transcribed!")
            return already_transcribed
        
        print(f"🔧 Transcription Configuration:")
        print(f"   • Episodes to transcribe: {len(episodes_to_transcribe)}")
        print(f"   • Worker processes/threads: {self.max_workers}")
        print(f"   • Execution mode: {'Multiprocessing' if self.use_multiprocessing else 'Threading'}")
        print(f"   • CPU cores available: {self.cpu_monitor.cpu_count}")
        
        # Start CPU monitoring
        self.cpu_monitor.start_monitoring()
        
        successful_transcriptions = 0
        
        try:
            if self.use_multiprocessing:
                # Use ProcessPoolExecutor for better CPU utilization
                print(f"🚀 Starting {self.max_workers} transcription processes...")
                
                with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                    # Convert EpisodeInfo to dict for multiprocessing
                    episode_dicts = []
                    for episode in episodes_to_transcribe:
                        episode_dict = {
                            'title': episode.title,
                            'audio_url': episode.audio_url,
                            'published': episode.published,
                            'episode_id': episode.episode_id,
                            'audio_path': episode.audio_path,
                            'transcript_path': episode.transcript_path,
                            'safe_title': episode.safe_title
                        }
                        episode_dicts.append(episode_dict)
                    
                    # Submit all transcription jobs
                    future_to_episode = {
                        executor.submit(transcribe_audio_worker_func, episode_dict): episode_dict 
                        for episode_dict in episode_dicts
                    }
                    
                    # Process completed transcriptions
                    for future in as_completed(future_to_episode):
                        episode_dict, success = future.result()
                        
                        if success:
                            successful_transcriptions += 1
                            # Mark episode as processed
                            episode_data = {
                                'title': episode_dict['title'],
                                'published': episode_dict['published'],
                                'audio_url': episode_dict['audio_url'],
                                'audio_file': episode_dict['audio_path'].name,
                                'transcript_file': episode_dict['transcript_path'].name
                            }
                            self.mark_episode_processed(episode_dict['episode_id'], episode_data)
            
            else:
                # Use ThreadPoolExecutor (original approach)
                print(f"🚀 Starting {self.max_workers} transcription threads...")
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # Submit all transcription jobs
                    future_to_episode = {
                        executor.submit(self.transcribe_audio_worker, episode): episode 
                        for episode in episodes_to_transcribe
                    }
                    
                    # Process completed transcriptions
                    for future in as_completed(future_to_episode):
                        episode_info, success = future.result()
                        
                        if success:
                            successful_transcriptions += 1
                            # Mark episode as processed
                            episode_data = {
                                'title': episode_info.title,
                                'published': episode_info.published,
                                'audio_url': episode_info.audio_url,
                                'audio_file': episode_info.audio_path.name,
                                'transcript_file': episode_info.transcript_path.name
                            }
                            self.mark_episode_processed(episode_info.episode_id, episode_data)
        
        finally:
            # Stop CPU monitoring
            self.cpu_monitor.stop_monitoring()
        
        print(f"\n📊 Transcription Summary:")
        print(f"   • Successfully transcribed: {successful_transcriptions} episodes")
        print(f"   • Already had transcripts: {already_transcribed} episodes")
        print(f"   • Failed: {len(episodes_to_transcribe) - successful_transcriptions} episodes")
        
        return successful_transcriptions + already_transcribed
    
    def process_podcast_feed(self, rss_url, max_episodes=None):
        """Download and transcribe episodes from a podcast RSS feed"""
        try:
            # Phase 1: Parse feed
            episodes = self.parse_episodes_from_feed(rss_url, max_episodes)
            if not episodes:
                return
            
            # Phase 2: Download episodes
            downloaded_episodes = self.download_episodes(episodes)
            if not downloaded_episodes:
                print("❌ No episodes were successfully downloaded")
                return
            
            # Phase 3: Transcribe episodes in parallel
            transcribed_count = self.transcribe_episodes(downloaded_episodes)
            
            print(f"\n🎉 === PROCESSING COMPLETE ===")
            print(f"📁 Audio files: {self.downloads_dir}")
            print(f"📄 Transcripts: {self.transcripts_dir}")
            print(f"📊 Total transcribed: {transcribed_count} episodes")
                
        except Exception as e:
            print(f"❌ Error processing feed: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python podcast_downloader.py <RSS_URL> [max_episodes] [max_workers] [--threading]")
        print("Example: python podcast_downloader.py https://feeds.npr.org/510289/podcast.xml 5 auto")
        print("  max_workers: Number of parallel workers ('auto' for optimal, default: auto)")
        print("  --threading: Use threading instead of multiprocessing (default: multiprocessing)")
        sys.exit(1)
    
    rss_url = sys.argv[1]
    max_episodes = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Parse max_workers argument
    max_workers = None
    if len(sys.argv) > 3:
        workers_arg = sys.argv[3]
        if workers_arg.lower() == 'auto':
            max_workers = None  # Will auto-detect
        else:
            max_workers = int(workers_arg)
    
    # Check for threading flag
    use_multiprocessing = '--threading' not in sys.argv
    
    print(f"🚀 Starting podcast downloader...")
    downloader = PodcastDownloader(max_workers=max_workers, use_multiprocessing=use_multiprocessing)
    downloader.process_podcast_feed(rss_url, max_episodes)

if __name__ == "__main__":
    main() 