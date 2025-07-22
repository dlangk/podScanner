#!/usr/bin/env python3
"""
Apple Podcasts RSS Feed Extractor

Extract RSS feed URLs from Apple Podcasts URLs
"""

import requests
import re
import sys
from urllib.parse import urlparse, parse_qs

def extract_rss_from_apple_podcasts(apple_url):
    """Extract RSS feed URL from Apple Podcasts URL"""
    try:
        print(f"🍎 Extracting RSS from Apple Podcasts URL: {apple_url}")
        
        # Method 1: Try to extract podcast ID from URL
        podcast_id = None
        
        # Parse URL patterns like:
        # https://podcasts.apple.com/us/podcast/podcast-name/id1234567890
        # https://podcasts.apple.com/podcast/podcast-name/id1234567890
        id_match = re.search(r'/id(\d+)', apple_url)
        if id_match:
            podcast_id = id_match.group(1)
        
        if not podcast_id:
            print("❌ Could not extract podcast ID from URL")
            return None
        
        print(f"📱 Found podcast ID: {podcast_id}")
        
        # Method 2: Use iTunes Search API to get RSS feed
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

def extract_rss_from_webpage(url):
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

def main():
    if len(sys.argv) < 2:
        print("Usage: python apple_podcast_extractor.py <APPLE_PODCASTS_URL_OR_ANY_URL>")
        print("\nExamples:")
        print("  python apple_podcast_extractor.py 'https://podcasts.apple.com/us/podcast/the-daily/id1200361736'")
        print("  python apple_podcast_extractor.py 'https://some-podcast-website.com'")
        sys.exit(1)
    
    url = sys.argv[1]
    rss_url = None
    
    # Check if it's an Apple Podcasts URL
    if 'podcasts.apple.com' in url:
        rss_url = extract_rss_from_apple_podcasts(url)
    else:
        # Try generic webpage extraction
        rss_url = extract_rss_from_webpage(url)
    
    if rss_url:
        print(f"\n🎉 Success! Use this RSS feed with your podcast downloader:")
        print(f"python podcast_downloader.py '{rss_url}' 5")
    else:
        print(f"\n😞 Could not find RSS feed for: {url}")
        print("\nAlternative approaches:")
        print("1. Check the podcast's official website")
        print("2. Use yt-dlp for YouTube-hosted podcasts")
        print("3. Use podcast-dl or similar tools")

if __name__ == "__main__":
    main() 