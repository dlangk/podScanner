#!/usr/bin/env python3
"""
Generic RSS feed extractor for websites
"""

import requests
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

def extract_rss_from_website(url: str) -> Optional[str]:
    """Try to find RSS feed URL from a generic website
    
    Args:
        url: Website URL
        
    Returns:
        RSS feed URL if found, None otherwise
    """
    try:
        print(f"🌐 Searching for RSS feed on: {url}")
        
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        content = response.text
        
        # Look for RSS feed links in various patterns
        patterns = [
            # Standard RSS link tags
            r'<link[^>]+type=["\']application/rss\+xml["\'][^>]+href=["\']([^"\']+)["\']',
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/rss\+xml["\']',
            # Atom feeds
            r'<link[^>]+type=["\']application/atom\+xml["\'][^>]+href=["\']([^"\']+)["\']',
            # Common RSS URLs
            r'href=["\']([^"\']+(?:feed|rss|podcast)[^"\']*\.(?:xml|rss))["\']',
            # iTunes/Apple Podcasts meta tags
            r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+podcasts\.apple\.com[^"\']+)["\']',
        ]
        
        found_feeds = []
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Make URL absolute
                feed_url = urljoin(url, match)
                if feed_url not in found_feeds:
                    found_feeds.append(feed_url)
        
        # Try common RSS paths if no feeds found
        if not found_feeds:
            common_paths = ['/feed', '/rss', '/feed.xml', '/rss.xml', '/podcast.xml', 
                          '/feed/podcast', '/feeds/posts/default', '/atom.xml']
            
            base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
            for path in common_paths:
                try:
                    test_url = base_url + path
                    test_response = requests.head(test_url, headers=headers, timeout=5, allow_redirects=True)
                    if test_response.status_code == 200:
                        content_type = test_response.headers.get('content-type', '').lower()
                        if any(ct in content_type for ct in ['xml', 'rss', 'atom']):
                            found_feeds.append(test_url)
                except:
                    continue
        
        if found_feeds:
            # Return the first feed found
            feed_url = found_feeds[0]
            print(f"✅ Found RSS feed: {feed_url}")
            if len(found_feeds) > 1:
                print(f"ℹ️  Found {len(found_feeds)} feeds total, using the first one")
            return feed_url
        
        print("❌ No RSS feed found on the website")
        return None
        
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error searching for RSS: {e}")
        return None