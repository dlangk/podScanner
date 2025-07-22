#!/usr/bin/env python3
"""
Main entry point for podScanner
Lightweight orchestrator that routes requests to appropriate handlers
"""

import sys
from podscanner import PodScanner

def print_usage():
    """Print usage information"""
    print("podScanner")
    print("=" * 50)
    print("Usage: python main.py <URL> [max_episodes] [options]")
    print("\nSupported sources:")
    print("  🍎 Apple Podcasts  - https://podcasts.apple.com/...")
    print("  📺 YouTube         - https://youtube.com/...")  
    print("  📡 RSS Feeds       - https://example.com/feed.rss")
    print("  🌐 Websites        - https://podcast-website.com")
    print("  🎵 Spotify         - Limited support")
    print("\nExamples:")
    print("  python main.py 'https://podcasts.apple.com/us/podcast/the-daily/id1200361736' 5")
    print("  python main.py 'https://youtube.com/playlist?list=...' 10")
    print("  python main.py 'https://feeds.npr.org/510289/podcast.xml' 3")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    url = sys.argv[1]
    max_episodes = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Create scanner and process the URL
    scanner = PodScanner()
    scanner.scan_and_download(url, max_episodes)

if __name__ == "__main__":
    main() 