#!/usr/bin/env python3
"""
Podcast Transcriber Module

Handles parallel transcription with CPU optimization.
"""

import os
import whisper
import multiprocessing
import psutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

from models import EpisodeInfo, DownloadConfig, ProcessingStats

def transcribe_audio_worker_func(episode_info_dict: dict) -> Tuple[dict, bool]:
    """Standalone worker function for multiprocessing"""
    import whisper
    from pathlib import Path
    from models import EpisodeInfo
    
    # Reconstruct EpisodeInfo from dict
    episode_info = EpisodeInfo(**episode_info_dict)
    
    try:
        # Load Whisper model in this process
        print(f"🎙️  [PID {os.getpid()}] Loading Whisper & transcribing: {episode_info.safe_title}")
        model = whisper.load_model("base")
        
        result = model.transcribe(str(episode_info.audio_path))
        transcript = result["text"]
        
        # Write transcript
        with open(episode_info.transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"Title: {episode_info.title}\n")
            f.write(f"URL: {episode_info.audio_url}\n")
            f.write(f"Published: {episode_info.published}\n")
            f.write(f"Episode ID: {episode_info.episode_id}\n")
            f.write(f"\n--- TRANSCRIPT ---\n\n")
            f.write(transcript)
        
        print(f"✅ [PID {os.getpid()}] Transcribed: {episode_info.safe_title}")
        return episode_info_dict, True
        
    except Exception as e:
        print(f"❌ [PID {os.getpid()}] Error transcribing {episode_info.safe_title}: {e}")
        return episode_info_dict, False

class CPUMonitor:
    """Monitor CPU usage and suggest optimal worker count"""
    
    def __init__(self):
        self.cpu_count = multiprocessing.cpu_count()
        self.monitoring = False
        self.cpu_history = []
        
    def get_optimal_workers(self, current_workers=None) -> int:
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

class PodcastTranscriber:
    """Handles parallel transcription with CPU optimization"""
    
    def __init__(self, config: DownloadConfig):
        self.config = config
        self.cpu_monitor = CPUMonitor()
        
        # Auto-determine optimal workers if not specified
        if config.max_workers is None:
            self.max_workers = self.cpu_monitor.get_optimal_workers()
        else:
            self.max_workers = config.max_workers
            self.cpu_monitor.get_optimal_workers(config.max_workers)
        
        # Don't load Whisper model here - load it in transcription workers
        self.whisper_model = None
    
    def load_whisper_model(self):
        """Load Whisper model (called by transcription workers)"""
        if self.whisper_model is None:
            print(f"🎙️  [Worker] Loading Whisper model...")
            self.whisper_model = whisper.load_model("base")
            print(f"🎙️  [Worker] Whisper model loaded!")
        return self.whisper_model
    
    def transcribe_audio_worker(self, episode_info: EpisodeInfo) -> Tuple[EpisodeInfo, bool]:
        """Worker function to transcribe a single audio file (ThreadPool version)"""
        try:
            # Load Whisper model in this worker
            model = self.load_whisper_model()
            
            print(f"🎙️  [Thread] Transcribing: {episode_info.safe_title}")
            result = model.transcribe(str(episode_info.audio_path))
            transcript = result["text"]
            
            # Write transcript
            with open(episode_info.transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"Title: {episode_info.title}\n")
                f.write(f"URL: {episode_info.audio_url}\n")
                f.write(f"Published: {episode_info.published}\n")
                f.write(f"Episode ID: {episode_info.episode_id}\n")
                f.write(f"\n--- TRANSCRIPT ---\n\n")
                f.write(transcript)
            
            print(f"✅ [Thread] Transcribed: {episode_info.safe_title}")
            return episode_info, True
            
        except Exception as e:
            print(f"❌ [Thread] Error transcribing {episode_info.safe_title}: {e}")
            return episode_info, False
    
    def transcribe_episodes(self, episodes: List[EpisodeInfo], mark_processed_callback) -> ProcessingStats:
        """Transcribe episodes in parallel, return transcription stats"""
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
            return ProcessingStats(
                total_episodes=len(episodes),
                already_transcribed=already_transcribed
            )
        
        print(f"🔧 Transcription Configuration:")
        print(f"   • Episodes to transcribe: {len(episodes_to_transcribe)}")
        print(f"   • Worker processes/threads: {self.max_workers}")
        print(f"   • Execution mode: {'Multiprocessing' if self.config.use_multiprocessing else 'Threading'}")
        print(f"   • CPU cores available: {self.cpu_monitor.cpu_count}")
        
        # Start CPU monitoring
        self.cpu_monitor.start_monitoring()
        
        successful_transcriptions = 0
        
        try:
            if self.config.use_multiprocessing:
                successful_transcriptions = self._transcribe_with_processes(
                    episodes_to_transcribe, mark_processed_callback
                )
            else:
                successful_transcriptions = self._transcribe_with_threads(
                    episodes_to_transcribe, mark_processed_callback
                )
        
        finally:
            # Stop CPU monitoring
            self.cpu_monitor.stop_monitoring()
        
        stats = ProcessingStats(
            total_episodes=len(episodes),
            transcribed=successful_transcriptions,
            already_transcribed=already_transcribed,
            failed=len(episodes_to_transcribe) - successful_transcriptions
        )
        
        print(f"\n📊 Transcription Summary:")
        print(f"   • Successfully transcribed: {successful_transcriptions} episodes")
        print(f"   • Already had transcripts: {already_transcribed} episodes")
        print(f"   • Failed: {stats.failed} episodes")
        
        return stats
    
    def _transcribe_with_processes(self, episodes: List[EpisodeInfo], mark_processed_callback) -> int:
        """Transcribe using ProcessPoolExecutor for maximum CPU utilization"""
        print(f"🚀 Starting {self.max_workers} transcription processes...")
        
        successful_transcriptions = 0
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Convert EpisodeInfo to dict for multiprocessing
            episode_dicts = []
            for episode in episodes:
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
                    mark_processed_callback(episode_dict['episode_id'], episode_data)
        
        return successful_transcriptions
    
    def _transcribe_with_threads(self, episodes: List[EpisodeInfo], mark_processed_callback) -> int:
        """Transcribe using ThreadPoolExecutor"""
        print(f"🚀 Starting {self.max_workers} transcription threads...")
        
        successful_transcriptions = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all transcription jobs
            future_to_episode = {
                executor.submit(self.transcribe_audio_worker, episode): episode 
                for episode in episodes
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
                    mark_processed_callback(episode_info.episode_id, episode_data)
        
        return successful_transcriptions 