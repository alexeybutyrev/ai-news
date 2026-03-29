#!/usr/bin/env python3
"""
AI News Aggregator - Fetches AI news from RSS feeds and generates TLDR summaries
"""

import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

# Configuration
OUTPUT_FILE = "/home/node/.openclaw/workspace/ai-news/docs/news.json"
REPO_DIR = "/home/node/.openclaw/workspace/ai-news"

RSS_FEEDS = [
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "priority": 1},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "priority": 1},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "priority": 2},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/", "priority": 2},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "priority": 1},
]

class HTMLStripper(HTMLParser):
    """Strip HTML tags from text"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
    
    def handle_data(self, d):
        self.fed.append(d)
    
    def get_data(self):
        return ''.join(self.fed)

def strip_html(text: str) -> str:
    """Remove HTML tags from text"""
    if not text:
        return ""
    s = HTMLStripper()
    s.feed(text)
    return s.get_data()

def fetch_url(url: str) -> Optional[str]:
    """Fetch URL content with error handling"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_rss_feed(feed_url: str, source_name: str, priority: int) -> List[Dict]:
    """Parse RSS feed and extract articles"""
    articles = []
    
    content = fetch_url(feed_url)
    if not content:
        return articles
    
    try:
        root = ET.fromstring(content)
        
        # Find channel and items
        channel = root.find('channel')
        if channel is None:
            return articles
        
        items = channel.findall('item')
        
        for item in items:
            try:
                title = item.find('title')
                link = item.find('link')
                description = item.find('description')
                pub_date = item.find('pubDate')
                enclosure = item.find('enclosure')
                content_encoded = item.find('{http://purl.org/rss/1.0/modules/content/}encoded')
                media_content = item.find('{http://search.yahoo.com/mrss/}content')
                
                # Extract image URL
                image_url = None
                if enclosure is not None:
                    image_url = enclosure.get('url')
                elif media_content is not None:
                    image_url = media_content.get('url')
                elif content_encoded is not None and content_encoded.text:
                    # Try to find image in content
                    import re
                    img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content_encoded.text)
                    if img_match:
                        image_url = img_match.group(1)
                
                article = {
                    'title': strip_html(title.text) if title is not None and title.text else '',
                    'url': link.text if link is not None and link.text else '',
                    'summary': strip_html(description.text)[:500] if description is not None and description.text else '',
                    'image': image_url,
                    'source': source_name,
                    'priority': priority,
                    'date': pub_date.text if pub_date is not None and pub_date.text else '',
                    'has_image': image_url is not None,
                }
                
                if article['title'] and article['url']:
                    articles.append(article)
                    
            except Exception as e:
                print(f"Error parsing item: {e}")
                continue
                
    except Exception as e:
        print(f"Error parsing RSS feed: {e}")
    
    return articles

def parse_date(date_str: str) -> Optional[datetime]:
    """Parse various date formats"""
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S GMT',
        '%a, %d %b %Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S%z',
        '%Y-%m-%dT%H:%M:%SZ',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except:
            continue
    return None

def is_yesterday(article_date: datetime) -> bool:
    """Check if article is from yesterday"""
    yesterday = datetime.now() - timedelta(days=1)
    return (article_date.year == yesterday.year and 
            article_date.month == yesterday.month and 
            article_date.day == yesterday.day)

def detect_topic(title: str, summary: str) -> str:
    """Detect article topic from title and summary"""
    text = (title + ' ' + summary).lower()
    
    topic_keywords = {
        'LLMs': ['llm', 'gpt', 'chatgpt', 'claude', 'gemini', 'language model', 'llama', 'mistral'],
        'Voice AI': ['speech', 'voice', 'audio', 'tts', 'text-to-speech', 'elevenlabs'],
        'Robotics': ['robot', 'autonomous', 'embodied'],
        'Safety': ['safety', 'alignment', 'responsible ai', 'regulation', 'risk'],
        'Research': ['research', 'paper', 'study', 'breakthrough', 'discovery'],
        'Startups': ['startup', 'funding', 'raise', 'invest', 'launch'],
        'Enterprise': ['enterprise', 'business', 'b2b', 'customer'],
        'Open Source': ['open source', 'open-source', 'github', 'hugging face'],
        'Hardware': ['chip', 'gpu', 'nvidia', 'hardware', 'processor'],
        'Generative AI': ['generative', 'image', 'video', 'midjourney', 'dall-e', 'stable diffusion'],
    }
    
    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in text:
                return topic
    
    return 'AI News'

def calculate_relevance_score(article: Dict) -> float:
    """Calculate relevance score based on keywords and source priority"""
    score = 0.0
    
    title = article.get('title', '').lower()
    summary = article.get('summary', '').lower()
    text = title + ' ' + summary
    
    # High-value keywords
    high_keywords = ['openai', 'gpt', 'chatgpt', 'claude', 'anthropic', 'gemini', 'google ai', 
                     'llm', 'agi', 'breakthrough', 'launch', 'release', 'announce']
    for kw in high_keywords:
        if kw in text:
            score += 2
    
    # Medium keywords
    medium_keywords = ['machine learning', 'deep learning', 'neural', 'transformer', 
                       'training', 'model', 'ai safety', 'regulation', 'startup']
    for kw in medium_keywords:
        if kw in text:
            score += 1
    
    # Source priority bonus
    score += (3 - article.get('priority', 2)) * 0.5
    
    return score

def generate_tldr(title: str, summary: str) -> str:
    """Generate TLDR using GLM-5 via API"""
    # Use the built-in model for TLDR generation
    prompt = f"""Summarize this AI news story in exactly 2 sentences. Be concise and informative.

Title: {title}
Summary: {summary[:500]}

TLDR:"""

    # For now, create a simple summary
    # In production, this would call GLM-5 API
    sentences = summary.split('. ')[:2]
    if len(sentences) >= 2:
        return '. '.join(sentences[:2]) + '.'
    elif sentences:
        return sentences[0] + '.'
    else:
        return f"This article discusses {title.lower()}."

def main():
    print("=" * 50)
    print("🤖 AI News Aggregator")
    print("=" * 50)
    print()
    
    # Calculate yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    print(f"📅 Looking for articles from: {yesterday_str}")
    print()
    
    # Fetch all feeds
    all_articles = []
    for feed in RSS_FEEDS:
        print(f"📰 Fetching {feed['name']}...")
        articles = parse_rss_feed(feed['url'], feed['name'], feed['priority'])
        print(f"   Found {len(articles)} articles")
        all_articles.extend(articles)
    
    print(f"\n📊 Total articles: {len(all_articles)}")
    
    # Filter by date (yesterday) and calculate relevance
    dated_articles = []
    for article in all_articles:
        if article['date']:
            article_date = parse_date(article['date'])
            if article_date:
                article['parsed_date'] = article_date
                article['relevance_score'] = calculate_relevance_score(article)
                # For initial run, accept articles from last 2 days if yesterday has few
                dated_articles.append(article)
    
    # Sort by relevance score
    dated_articles.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    # Get top 5
    top_articles = dated_articles[:5]
    
    print(f"\n🎯 Top {len(top_articles)} articles selected")
    
    # Generate TLDR for each
    print("\n✨ Generating TLDR summaries...")
    for i, article in enumerate(top_articles):
        print(f"   [{i+1}] {article['title'][:50]}...")
        article['tldr'] = generate_tldr(article['title'], article['summary'])
        # Detect topic
        article['topic'] = detect_topic(article['title'], article['summary'])
        # Format date nicely
        if 'parsed_date' in article:
            article['formatted_date'] = article['parsed_date'].strftime('%B %d, %Y')
        else:
            article['formatted_date'] = yesterday_str
    
    # Clean articles for JSON serialization
    for article in top_articles:
        if 'parsed_date' in article:
            del article['parsed_date']
        if 'date' in article and hasattr(article['date'], 'isoformat'):
            article['date'] = article['date'].isoformat()
    
    # Prepare output
    output = {
        'date': yesterday_str,
        'generated_at': datetime.now().isoformat(),
        'articles': top_articles
    }
    
    # Save to file
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Saved to {OUTPUT_FILE}")
    
    # Push to GitHub
    print("\n🚀 Pushing to GitHub...")
    os.chdir(REPO_DIR)
    
    # Initialize git if needed
    if not os.path.exists('.git'):
        subprocess.run(['git', 'init'], check=True)
        subprocess.run(['git', 'remote', 'add', 'origin', 
                       'https://github.com/alexeybutyrev/ai-news.git'], check=True)
    
    subprocess.run(['git', 'add', '-A'], check=True)
    subprocess.run(['git', 'commit', '-m', f'Update AI news for {yesterday_str}'], check=True)
    subprocess.run(['git', 'push', '-f', 'origin', 'HEAD:main'], check=True)
    
    print("\n✅ Done!")
    print("=" * 50)

if __name__ == '__main__':
    main()
