#!/usr/bin/env python3
"""
Apple Podcasts RSS extractor
"""

import requests
import re
from typing import Optional

def extract_apple_podcast_rss(apple_url: str) -> Optional[str]:
    """Extract RSS feed URL from Apple Podcasts URL
    
    Args:
        apple_url: Apple Podcasts URL
        
    Returns:
        RSS feed URL if found, None otherwise
    """
    try:
        print(f"🍎 Extracting RSS from: {apple_url}")
        
        # Extract podcast ID from URL
        # Patterns: /id1234567890, /podcast/name/id1234567890
        id_match = re.search(r'/id(\d+)', apple_url)
        if not id_match:
            print("❌ Could not extract podcast ID from URL")
            return None
        
        podcast_id = id_match.group(1)
        print(f"📱 Found podcast ID: {podcast_id}")
        
        # Use iTunes Search API to get RSS feed
        search_url = f"https://itunes.apple.com/lookup?id={podcast_id}&entity=podcast"
        
        response = requests.get(search_url, timeout=10)
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
        
        # Get podcast name for display
        podcast_name = podcast_info.get('collectionName', 'Unknown')
        print(f"✅ Found podcast: {podcast_name}")
        print(f"📡 RSS feed: {rss_url}")
        
        return rss_url
        
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error extracting RSS: {e}")
        return None