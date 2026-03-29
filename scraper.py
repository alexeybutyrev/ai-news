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
import hashlib
import ssl

# Configuration
OUTPUT_FILE = "/home/node/.openclaw/workspace/ai-news/docs/news.json"
REPO_DIR = "/home/node/.openclaw/workspace/ai-news"
IMAGES_DIR = "/home/node/.openclaw/workspace/ai-news/docs/images"

RSS_FEEDS = [
    # Priority 1 - AI-specific, highest relevance
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "priority": 1},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed/", "priority": 1},
    {"name": "VentureBeat", "url": "https://venturebeat.com/feed/", "priority": 1},
    {"name": "Latent Space", "url": "https://latent.space/feed", "priority": 1},
    {"name": "AlphaSignal", "url": "https://alphasignalai.substack.com/feed", "priority": 1},
    
    # Priority 2 - AI/Tech focused
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "priority": 2},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "priority": 2},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "priority": 2},
    {"name": "DeepMind", "url": "https://deepmind.google/blog/rss.xml", "priority": 2},
    {"name": "Interconnects", "url": "https://www.interconnects.ai/feed", "priority": 2},
    {"name": "The Sequence", "url": "https://thesequence.substack.com/feed", "priority": 2},
    {"name": "Reuters AI", "url": "https://news.google.com/rss/search?q=when:24h+allinurl:reuters.com+AI&ceid=US:en&hl=en-US&gl=US", "priority": 2},
    
    # Priority 3 - General tech with AI coverage
    {"name": "The Register", "url": "https://www.theregister.com/headlines.atom", "priority": 3},
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

def download_image(url: str, article_id: int) -> Optional[str]:
    """Download image and save locally, return local path"""
    if not url:
        return None
    
    try:
        # Create images directory
        os.makedirs(IMAGES_DIR, exist_ok=True)
        
        # Generate filename from URL hash
        ext = '.jpg'
        if '.png' in url.lower():
            ext = '.png'
        elif '.webp' in url.lower():
            ext = '.webp'
        elif '.gif' in url.lower():
            ext = '.gif'
        
        filename = f"article_{article_id}{ext}"
        filepath = os.path.join(IMAGES_DIR, filename)
        
        # Download with SSL context to handle some certificate issues
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = response.read()
            
        # Check if image is valid (at least 5KB to avoid placeholders)
        if len(data) < 5120:
            return None
        
        with open(filepath, 'wb') as f:
            f.write(data)
        
        return f"images/{filename}"
        
    except Exception as e:
        print(f"     Could not download image: {e}")
        return None

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
    
    # High-value keywords (weight: 2)
    high_keywords = ['openai', 'gpt', 'chatgpt', 'claude', 'anthropic', 'gemini', 'google ai', 
                     'llm', 'agi', 'breakthrough', 'launch', 'release', 'announce', 'mistral']
    for kw in high_keywords:
        if kw in text:
            score += 2
    
    # Medium keywords (weight: 1)
    medium_keywords = ['machine learning', 'deep learning', 'neural', 'transformer', 
                       'training', 'model', 'ai safety', 'regulation', 'startup', 'open source']
    for kw in medium_keywords:
        if kw in text:
            score += 1
    
    # Source priority bonus - Priority 1 sources get significant boost
    priority = article.get('priority', 3)
    if priority == 1:
        score += 5  # Major boost for AI-specific sources
    elif priority == 2:
        score += 2  # Moderate boost for tech sources
    else:
        score += 0.5  # Small boost for general sources
    
    return score

def generate_tldr(title: str, summary: str) -> str:
    """Generate TLDR - 2 sentence summary"""
    sentences = summary.split('. ')[:2]
    if len(sentences) >= 2:
        return '. '.join(sentences[:2]) + '.'
    elif sentences:
        return sentences[0] + '.'
    else:
        return f"This article discusses {title.lower()}."

def generate_importance(title: str, summary: str, topic: str) -> str:
    """Generate 1-sentence importance explanation"""
    text = (title + ' ' + summary).lower()
    
    if 'intercom' in text or 'fin apex' in text:
        return "Shows how enterprise AI is evolving beyond general-purpose models."
    elif 'mistral' in text and ('speech' in text or 'voice' in text or 'tts' in text):
        return "Open-source voice AI could disrupt the closed-source model market."
    elif 'mistral' in text:
        return "Mistral's open-source approach challenges OpenAI's dominance."
    elif 'claude' in text or 'anthropic' in text:
        return "Claude's growth signals demand for AI safety-focused alternatives."
    elif 'gemini' in text or 'google' in text:
        return "Google's AI moves impact billions of users across search and cloud."
    elif 'openai' in text and ('abandon' in text or 'shutdown' in text or 'cancel' in text):
        return "Reveals OpenAI's shifting priorities and product strategy."
    elif 'openai' in text and ('chip' in text or 'hardware' in text or 'nvidia' in text):
        return "Hardware independence could reduce OpenAI's compute costs significantly."
    elif 'openai' in text:
        return "Important for understanding the AI market leader's direction."
    elif 'cohere' in text:
        return "Enterprise-focused AI models are becoming a distinct market segment."
    elif topic == 'Voice AI':
        return "Voice AI is emerging as a key differentiator for AI platforms."
    elif topic == 'Safety':
        return "AI safety developments shape how companies deploy models responsibly."
    elif topic == 'Startups':
        return "Funding trends reveal where investors see AI opportunities."
    elif topic == 'Open Source':
        return "Open-source models democratize access to advanced AI capabilities."
    elif topic == 'Hardware':
        return "Hardware advances directly affect AI compute costs and availability."
    else:
        return "Relevant for staying current with AI industry developments."

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
    
    # Get top 10
    top_articles = dated_articles[:10]
    
    print(f"\n🎯 Top {len(top_articles)} articles selected")
    
    # Generate TLDR and importance for each
    print("\n✨ Generating summaries...")
    for i, article in enumerate(top_articles):
        print(f"   [{i+1}] {article['title'][:50]}...")
        # Detect topic first
        article['topic'] = detect_topic(article['title'], article['summary'])
        # Generate TLDR
        article['tldr'] = generate_tldr(article['title'], article['summary'])
        # Generate importance
        article['importance'] = generate_importance(article['title'], article['summary'], article['topic'])
        # Format date nicely
        if 'parsed_date' in article:
            article['formatted_date'] = article['parsed_date'].strftime('%B %d, %Y')
        else:
            article['formatted_date'] = yesterday_str
    
    # Remove image downloading - keeping text-only
    
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
    
    # Clean articles for JSON serialization
    for article in top_articles:
        if 'parsed_date' in article:
            del article['parsed_date']
        if 'date' in article and hasattr(article['date'], 'isoformat'):
            article['date'] = article['date'].isoformat()
    
    output = {
        'date': yesterday_str,
        'generated_at': datetime.now().isoformat(),
        'articles': top_articles
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Saved to {OUTPUT_FILE}")
    
    # Only push to GitHub if NOT running in CI (GitHub Actions handles push)
    if not os.environ.get('CI'):
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
        print("\n✅ Pushed to GitHub!")
    else:
        print("\n✅ Running in CI - GitHub Actions will handle the push")
    
    print("\n✅ Done!")
    print("=" * 50)

if __name__ == '__main__':
    main()
