#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Smart Trend Optimizer (YouTube + X/Twitter + Instagram + LinkedIn) - Multimedia Edition
---------------------------------------------------------------------------
- Analyzes text, images, and videos for trends
- Fetches related YouTube/X/Instagram/LinkedIn trends
- Provides specific, actionable optimization suggestions
"""
import ssl
import certifi
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
import os
import argparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from dotenv import load_dotenv
import google.generativeai as genai
import time
import random
from pathlib import Path
from typing import Union
import json

# Load API key
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("Missing GOOGLE_API_KEY in .env file")

genai.configure(api_key=API_KEY)

# Gemini model configuration
MODEL = "gemini-2.5-flash"
VISION_MODEL = "gemini-2.5-flash"  # Same model supports multimodal

# ----------------------------
# Trend Detection
# ----------------------------
def detect_trends(content: Union[str, list]) -> list:
    """Automatically extract trending topics from text or media"""
    if isinstance(content, str):
        # Text analysis
        prompt = f"""
        Analyze this text and identify the 3 most relevant trending topics:
        {content}
        
        Return ONLY a comma-separated list of keywords.
        Example: "social media, content marketing, viral trends"
        """
    else:
        # Media analysis (list of files)
        prompt = """
        Analyze these images/videos and identify the 3 most relevant trending topics.
        Consider visual elements, context, and potential viral aspects.
        
        Return ONLY a comma-separated list of keywords.
        Example: "street fashion, urban photography, sneaker culture"
        """
    
    try:
        if isinstance(content, str):
            response = genai.GenerativeModel(MODEL).generate_content(prompt)
        else:
            media_parts = [genai.upload_file(m) for m in content]
            response = genai.GenerativeModel(VISION_MODEL).generate_content(
                [prompt] + media_parts
            )
            
        trends = [x.strip() for x in response.text.split(",")][:3]
        return [t for t in trends if t]  # Filter empty strings
    except Exception as e:
        print(f"Trend detection error: {e}")
        return ["viral content"]  # Fallback

# ----------------------------
# Media Processing
# ----------------------------
def process_media(file_path: Union[str, list]) -> list:
    """Handle single file or list of files"""
    if isinstance(file_path, str):
        return [file_path]
    return file_path

def validate_media(file_path: str) -> bool:
    """Check if file is valid image/video"""
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.webm']
    return Path(file_path).suffix.lower() in valid_extensions

# ----------------------------
# Data Scrapers
# ----------------------------
def get_youtube_trends(keyword, max_items=5):
    """Get YouTube trends for specific keyword"""
    url = f"https://www.youtube.com/results?search_query={quote_plus(keyword)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        return [
            (a.get("title") or a.text).strip()
            for a in soup.select("a#video-title")[:max_items]
        ]
    except Exception as e:
        print(f"YouTube Error: {e}")
        return []
    
def get_x_trends(keyword, max_items=5):
    """Get Twitter trends using Nitter"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    url = f"https://nitter.net/search?f=tweets&q={quote_plus(keyword)}%20lang%3Aen"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        return [
            div.get_text(strip=True) 
            for div in soup.select('div.tweet-content')[:max_items]]
    except Exception as e:
        print(f"Twitter Error: {e}")
        return []

def get_instagram_trends(keyword, max_items=5):
    """Get Instagram trends using multiple approaches with better fallbacks"""
    # First try: Use Instagram's official graphql endpoint (public data)
    try:
        print("Attempting Instagram public API...")
        url = f"https://www.instagram.com/explore/tags/{quote_plus(keyword)}/?__a=1&__d=dis"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.instagram.com/",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            posts = data.get('graphql', {}).get('hashtag', {}).get('edge_hashtag_to_media', {}).get('edges', [])
            trends = []
            for post in posts[:max_items]:
                if post.get('node', {}).get('edge_media_to_caption', {}).get('edges', []):
                    text = post['node']['edge_media_to_caption']['edges'][0]['node']['text']
                    trends.append(text)
                    # Extract hashtags from caption
                    trends.extend([tag for tag in text.split() if tag.startswith('#')])
            if trends:
                return list(set(trends))[:max_items]
    except Exception as e:
        print(f"Instagram API Error: {str(e)[:100]}...")

    # Second try: Use Google search to find Instagram posts
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    ]

    try:
        print("Attempting Google search fallback...")
        google_url = f"https://www.google.com/search?q=site:instagram.com+{quote_plus(keyword)}"
        headers = {"User-Agent": random.choice(user_agents)}
        
        response = requests.get(google_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            trends = []
            for result in soup.select('div.g')[:max_items]:
                title = result.select_one('h3')
                if title:
                    trends.append(title.get_text(strip=True))
            if trends:
                return trends[:max_items]
    except Exception as e:
        print(f"Google search fallback error: {str(e)[:100]}...")

    # Final fallback: Use AI to generate relevant hashtags and content ideas
    try:
        print("Using AI fallback for Instagram trends...")
        prompt = f"""
        Generate {max_items} relevant Instagram post ideas and hashtags for: {keyword}
        Return as a comma-separated list.
        Example: "Beautiful sunset at the beach #sunset #nature, Portrait photography tips #photography #tips"
        """
        response = genai.GenerativeModel(MODEL).generate_content(prompt)
        trends = [x.strip() for x in response.text.split(",")][:max_items]
        return trends if trends else get_manual_fallback(keyword, max_items)
    except:
        return get_manual_fallback(keyword, max_items)
   

def get_linkedin_trends(keyword, max_items=5):
    """Get LinkedIn trends using multiple approaches"""
    # Approach 1: LinkedIn public posts search
    try:
        print("Attempting LinkedIn public search...")
        url = f"https://www.linkedin.com/search/results/content/?keywords={quote_plus(keyword)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            trends = []
            for post in soup.select('div.feed-shared-update-v2__description-wrapper')[:max_items]:
                text = post.get_text(separator=' ', strip=True)
                if text:
                    trends.append(text)
            if trends:
                return trends[:max_items]
    except Exception as e:
        print(f"LinkedIN public search error: {str(e)[:100]}...")

    # Approach 2: Google search for LinkedIn posts
    try:
        print("Trying Google search for LinkedIn posts...")
        google_url = f"https://www.google.com/search?q=site:linkedin.com+{quote_plus(keyword)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(google_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            trends = []
            for result in soup.select('div.g')[:max_items]:
                title = result.select_one('h3')
                if title:
                    trends.append(title.get_text(strip=True))
            if trends:
                return trends[:max_items]
    except Exception as e:
        print(f"Google search for LinkedIn error: {str(e)[:100]}...")

    # Approach 3: AI-generated LinkedIn content suggestions
    try:
        print("Using AI for LinkedIn trends...")
        prompt = f"""
        Generate {max_items} professional LinkedIn post ideas about: {keyword}
        Focus on business insights, career advice, and industry trends.
        Return as a comma-separated list.
        Example: "How {keyword} is transforming our industry, 3 ways to leverage {keyword} in your business"
        """
        response = genai.GenerativeModel(MODEL).generate_content(prompt)
        trends = [x.strip() for x in response.text.split(",")][:max_items]
        return trends if trends else get_linkedin_fallback(keyword, max_items)
    except Exception as e:
        print(f"AI LinkedIn generation error: {str(e)[:100]}...")
        return get_linkedin_fallback(keyword, max_items)

def get_linkedin_fallback(keyword, max_items):
    """Fallback LinkedIn content suggestions"""
    return [
        f"Industry insights about {keyword}",
        f"How {keyword} is changing business",
        f"Professional perspectives on {keyword}",
        f"Career advice related to {keyword}",
        f"Business applications of {keyword}"
    ][:max_items]

def get_manual_fallback(keyword, max_items):
    """Final manual fallback when all else fails"""
    base_hashtags = [
        f"#{keyword.replace(' ', '')}",
        f"#{keyword.replace(' ', '_')}",
        f"#{keyword.replace(' ', '')}photography",
        f"#{keyword.replace(' ', '')}lover",
        f"#{keyword.replace(' ', '')}trend"
    ]
    return base_hashtags[:max_items]

# ----------------------------
# Analysis Engine
# ----------------------------
def generate_suggestions(content: Union[str, list], caption_text=None, manual_query=None) -> str:
    """Full analysis pipeline with automatic trend detection"""
    # Step 1: Process input
    is_media = not isinstance(content, str) or caption_text is not None
    processed_media = process_media(content) if is_media and not isinstance(content, str) else None
    
    # Validate media files if provided
    if processed_media:
        for file_path in processed_media:
            if not validate_media(file_path):
                return f"Error: Unsupported file format for {file_path}"
    
    # Step 2: Detect trends or use manual query
    if caption_text and processed_media:
        # Use both caption and media for trend detection
        trends = [manual_query] if manual_query else detect_trends(caption_text)
        print(f"Analyzing trends from caption: {', '.join(trends)}")
    elif processed_media:
        # Use only media for trend detection
        trends = [manual_query] if manual_query else detect_trends(processed_media)
        print(f"Analyzing trends from media: {', '.join(trends)}")
    else:
        # Use only text for trend detection
        trends = [manual_query] if manual_query else detect_trends(content)
        print(f"Analyzing trends from text: {', '.join(trends)}")
    
    # Step 3: Gather platform data
    youtube_data = {}
    twitter_data = {}
    instagram_data = {}
    linkedin_data = {}
    
    for trend in trends:
        youtube_data[trend] = get_youtube_trends(trend)
        twitter_data[trend] = get_x_trends(trend)
        instagram_data[trend] = get_instagram_trends(trend)
        linkedin_data[trend] = get_linkedin_trends(trend)
        time.sleep(random.uniform(1, 2))  # Respectful delay
    
    # Step 4: Generate suggestions with specific action steps
    prompt_parts = []
    
    if processed_media and caption_text:
        prompt_parts.append(f"""
        CONTENT TO OPTIMIZE:
        - Media files: {len(processed_media)} files
        - File types: {[Path(f).suffix for f in processed_media]}
        - Caption text: "{caption_text}"
        """)
        
        # Add media files to prompt
        media_parts = [genai.upload_file(f) for f in processed_media]
        prompt_parts.extend(media_parts)
    elif processed_media:
        prompt_parts.append(f"""
        CONTENT TO OPTIMIZE:
        - Media files: {len(processed_media)} files
        - File types: {[Path(f).suffix for f in processed_media]}
        - No caption provided
        """)
        
        # Add media files to prompt
        media_parts = [genai.upload_file(f) for f in processed_media]
        prompt_parts.extend(media_parts)
    else:
        prompt_parts.append(f"CONTENT TO OPTIMIZE:\n\"{content}\"")
    
    prompt_parts.append(f"""
    DETECTED TRENDS:
    {trends}
    
    PLATFORM TREND DATA:
    - YouTube: {youtube_data}
    - Twitter/X: {twitter_data}
    - Instagram: {instagram_data}
    - LinkedIn: {linkedin_data}
    
    PROVIDE SPECIFIC, ACTIONABLE RECOMMENDATIONS:
    
    For each platform (YouTube, Twitter/X, Instagram, LinkedIn), give me EXACT instructions:
    
    1. EXACT CAPTION/TEXT CHANGES:
       - Rewrite the caption/text specifically for this platform
       - Tell me exactly what to change and what to write instead
       - Include specific phrases and CTAs to use
    
    2. EXACT VISUAL CHANGES (if media provided):
       - Specific edits to make to images/videos
       - Recommended filters, crops, or enhancements
       - What to add/remove from the visuals
    
    3. EXACT HASHTAGS TO USE:
       - List 5-10 specific hashtags for this platform
       - Format: #ExactlyLikeThis
    
    4. EXACT POSTING STRATEGY:
       - Best day/time to post (be specific: "Tuesday 2-4PM EST")
       - Recommended frequency
       - Platform-specific features to use
    
    5. ENGAGEMENT BOOSTING TACTICS:
       - Specific questions to ask in comments
       - How to respond to comments
       - Cross-promotion strategies
    
    STRUCTURE YOUR RESPONSE LIKE THIS:
    
    ===== YOUTUBE OPTIMIZATION =====
    [Specific instructions for YouTube]
    
    ===== TWITTER/X OPTIMIZATION =====
    [Specific instructions for Twitter/X]
    
    ===== INSTAGRAM OPTIMIZATION =====
    [Specific instructions for Instagram]
    
    ===== LINKEDIN OPTIMIZATION =====
    [Specific instructions for LinkedIn]
    
    Be extremely specific and prescriptive. Tell me exactly what to do, not just general advice.
    """)
    
    try:
        model = genai.GenerativeModel(VISION_MODEL if is_media else MODEL)
        response = model.generate_content(prompt_parts)
        return response.text
    except Exception as e:
        return f"Analysis Error: {str(e)}"

# ----------------------------
# Interfaces
# ----------------------------
def main():
    """Command line interface"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", help="Text to analyze")
    parser.add_argument("--caption", help="Caption text for media files")
    parser.add_argument("--file", help="File containing text or media (image/video)")
    parser.add_argument("--dir", help="Directory containing multiple media files")
    parser.add_argument("--query", help="Manual trend query (optional)")
    args = parser.parse_args()
    
    content = args.text
    caption = args.caption
    files = []
    
    if args.file:
        if os.path.isdir(args.file):
            files = [os.path.join(args.file, f) for f in os.listdir(args.file)]
        else:
            files = [args.file]
    elif args.dir:
        files = [os.path.join(args.dir, f) for f in os.listdir(args.dir)]
    
    if files:
        content = files
    elif not content and not caption:
        print("Error: No content provided")
        exit(1)
        
    print("Analyzing content..." if isinstance(content, str) and not caption else "Analyzing media with caption..." if caption else "Analyzing media...")
    suggestions = generate_suggestions(content, caption, args.query)
    
    print("\n=== OPTIMIZATION INSTRUCTIONS ===")
    print(suggestions)

def run_optimizer(text=None, caption=None, file_path=None, dir_path=None, query=None):
    """Django-compatible interface"""
    content = text
    files = []
    
    if file_path:
        if os.path.isdir(file_path):
            files = [os.path.join(file_path, f) for f in os.listdir(file_path)]
        else:
            files = [file_path]
    elif dir_path:
        files = [os.path.join(dir_path, f) for f in os.listdir(dir_path)]
    
    if files:
        content = files
    elif not content and not caption:
        raise ValueError("Either text, caption, file_path, or dir_path must be provided")
    
    return generate_suggestions(content, caption, query)

if __name__ == "__main__":
    main()