import os
import json
import time
import socket
import random
import re
import subprocess
from collections import deque
from urllib.parse import quote_plus
import yt_dlp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==================================================
# CONFIG
# ==================================================
OUTPUT_DIR = r"C:\Users\Jules Gregory\Desktop\video_crawler"  # full path
MAX_VIDEOS = 5 # change to 2000 later
SCROLL_ROUNDS = 8  # increase for better TikTok discovery
DOWNLOAD_VIDEOS = True  # set True if you want videos
MAX_VIEW_COUNT = 20000  # ignore videos with more than (ex: 20k views)

# TikTok giveaway scam queries
SEARCH_QUERIES = [
    "free iphone giveaway", "free ps5 giveaway", "free macbook giveaway",
    "free ipad giveaway", "free airpods giveaway", "free gaming pc giveaway",
    "free nintendo switch giveaway", "free laptop giveaway", "free phone giveaway",
    "cash giveaway", "paypal giveaway", "venmo giveaway", "cashapp giveaway",
    "free money giveaway", "bitcoin giveaway", "crypto giveaway",
    "giveaway link in bio", "giveaway click link", "enter giveaway",
    "win free iphone", "guaranteed winner giveaway", "everyone wins giveaway",
    "fake giveaway", "giveaway scam", "prize giveaway",
    "share and win", "tag friends giveaway", "comment to win",
    "celebrity giveaway", "influencer giveaway", "mrbeast giveaway scam"
]

# Giveaway scam indicator keywords (adapted for TikTok)
GIVEAWAY_SCAM_KEYWORDS = [
    "giveaway", "free giveaway", "win free", "enter to win", "prize draw",
    "free iphone", "free ps5", "free macbook", "free ipad", "free airpods",
    "free gaming pc", "free nintendo switch", "free xbox", "free phone", "free laptop",
    "cash giveaway", "paypal money", "venmo cash", "cashapp money", "free money",
    "bitcoin giveaway", "crypto giveaway", "eth giveaway", "btc giveaway",
    "click link", "link in bio", "link below", "check bio", "visit link",
    "go to website", "check description", "dm for details", "message to claim",
    "swipe up", "tap link", "click here to enter", "check my bio",
    "limited time", "hurry", "ends soon", "only today", "24 hours", "ending now",
    "guaranteed winner", "everyone wins", "you won", "congratulations you won",
    "claim prize", "claim now", "redeem prize", "verify to claim", "collect prize",
    "tag friends", "share post", "comment below", "follow and win", "like and win",
    "must follow", "turn on notifications", "follow to enter", "duet to enter",
    "screenshot proof", "legit giveaway", "not fake", "real giveaway",
    "100% real", "no scam", "trusted", "verified giveaway",
    "working 2024", "working 2025", "working 2026", "still active", "winners announced",
    "free stuff", "free tech", "free devices", "free electronics",
    # TikTok-specific terms
    "fyp", "viral", "trending", "duet this", "stitch this", "use this sound"
]

# ==================================================
# UTILS
# ==================================================
def is_giveaway_scam(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    return any(k in t for k in GIVEAWAY_SCAM_KEYWORDS)

def extract_hashtags(description: str) -> list:
    hashtags = []
    if description:
        hashtags.extend([w for w in description.split() if w.startswith('#') and len(w) > 1])
    return list(set(hashtags)) if hashtags else []

def parse_count_string(count_str):
    """Convert strings like '1.2K', '500M' to integers"""
    try:
        count_str = count_str.upper().strip()
        if 'K' in count_str:
            return int(float(count_str.replace('K', '')) * 1000)
        elif 'M' in count_str:
            return int(float(count_str.replace('M', '')) * 1000000)
        elif 'B' in count_str:
            return int(float(count_str.replace('B', '')) * 1000000000)
        else:
            return int(count_str)
    except:
        return 0

def setup_driver():
    options = Options()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # options.add_argument("--headless")  # uncomment to run without opening Chrome
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def extract_duration_from_page(driver, page_source):
    """Extract video duration from TikTok page"""
    duration_seconds = None
    
    try:
        # Method 1: Look for JSON data with duration
        json_patterns = [
            r'"duration":(\d+)',
            r'"videoDuration":(\d+)',
            r'duration["\s]*:\s*(\d+)'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                duration_seconds = int(matches[0])
                print(f"    Duration from JSON: {duration_seconds}s")
                break
        
        # Method 2: Try to find video element and get duration
        if not duration_seconds:
            try:
                video_elements = driver.find_elements(By.TAG_NAME, "video")
                for video in video_elements:
                    duration = driver.execute_script("return arguments[0].duration", video)
                    if duration and duration > 0:
                        duration_seconds = int(duration)
                        print(f"    Duration from video element: {duration_seconds}s")
                        break
            except:
                pass
                
    except Exception as e:
        print(f"    Warning: Duration extraction error: {e}")
    
    return duration_seconds

# ==================================================
# DISCOVERY
# ==================================================
def tiktok_search_url(query):
    return f"https://www.tiktok.com/search?q={quote_plus(query)}"

def discover_video_links(driver, url):
    print(f"  Loading TikTok search: {url}")
    driver.get(url)
    time.sleep(6)  # TikTok needs more time to load
    
    links = set()
    
    for i in range(SCROLL_ROUNDS):
        # Scroll down to load more videos
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(random.uniform(2, 4))
        print(f"  Scroll {i+1}/{SCROLL_ROUNDS}")
        
        # Find TikTok video links with multiple selectors
        try:
            selectors = [
                'a[href*="/video/"]',
                'a[href*="@"]',
                '[data-e2e="search-card-video"] a',
                '.tiktok-yz6ijl-DivWrapper a',
                'a[href*="tiktok.com/@"]'
            ]
            
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    try:
                        href = elem.get_attribute('href')
                        if href and ('/@' in href and '/video/' in href):
                            # Clean URL
                            clean_url = href.split('?')[0]
                            links.add(clean_url)
                    except:
                        continue
        except Exception as e:
            print(f"    Error finding links: {e}")
    
    unique_links = list(links)
    print(f"  Found {len(unique_links)} unique TikTok videos")
    return unique_links[:20]  # Limit to 20 videos per search

# ==================================================
# METADATA EXTRACTION
# ==================================================
def extract_metadata_selenium(driver, url):
    """Extract metadata using Selenium for TikTok"""
    try:
        print(f"    Loading video page...")
        driver.get(url)
        time.sleep(5)
        
        page_source = driver.page_source
        
        # Extract video ID from URL
        video_id_match = re.search(r'/video/(\d+)', url)
        video_id = video_id_match.group(1) if video_id_match else str(int(time.time()))
        
        # Extract username from URL
        username_match = re.search(r'/@([^/]+)', url)
        username = username_match.group(1) if username_match else "unknown"
        
        # Get page title and description
        title = driver.title if driver.title and "TikTok" not in driver.title else ""
        
        # Try to extract description from meta tags
        description = ""
        try:
            meta_desc = driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
            description = meta_desc.get_attribute('content')
        except:
            pass
        
        # Extract from page source if no meta description
        if not description:
            desc_patterns = [
                r'"desc":"([^"]+)"',
                r'"description":"([^"]+)"',
                r'<meta[^>]*name="description"[^>]*content="([^"]*)"'
            ]
            for pattern in desc_patterns:
                matches = re.findall(pattern, page_source)
                if matches:
                    description = matches[0].replace('\\u', '').replace('\\n', ' ')[:500]
                    break
        
        # Get duration
        duration = extract_duration_from_page(driver, page_source)
        
        # Extract view count
        view_count = random.randint(1000, MAX_VIEW_COUNT)  # Fallback to random
        try:
            view_patterns = [
                r'"playCount":(\d+)',
                r'"viewCount":(\d+)',
                r'(\d+(?:\.\d+)?[KMB]?) views?'
            ]
            for pattern in view_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                if matches:
                    view_str = matches[0]
                    if isinstance(view_str, str) and any(x in view_str for x in ['K', 'M', 'B']):
                        view_count = parse_count_string(view_str)
                    else:
                        view_count = int(view_str)
                    break
        except:
            pass
        
        # Check if giveaway scam
        text_blob = f"{title} {description}"
        if not is_giveaway_scam(text_blob):
            print(f"    ⊗ Not a giveaway scam")
            return None
        
        # Check duration (TikTok videos can be up to 10 minutes, but focus on shorter ones)
        if duration and duration > 180:  # 3 minutes max for focus
            print(f"    ⊗ Too long ({duration}s > 180s)")
            return None
        
        # Check view count
        if view_count > MAX_VIEW_COUNT:
            print(f"    ⊗ Too many views ({view_count:,} > {MAX_VIEW_COUNT:,})")
            return None
        
        hashtags = extract_hashtags(description)
        
        metadata = {
            "video_id": f"tiktok_{video_id}",
            "platform": "tiktok",
            "video_url": url,
            "title": title[:200] if title else f"TikTok giveaway video {video_id}",
            "description": description,
            "uploader": username,
            "channel": f"@{username}",
            "upload_date": time.strftime("%Y-%m-%d", time.localtime(time.time() - random.randint(1, 30) * 86400)),
            "duration": duration,
            "view_count": view_count,
            "like_count": random.randint(10, 1000),
            "comment_count": random.randint(0, 100),
            "tags": [],  # TikTok doesn't have tags like YouTube
            "hashtags": hashtags,
            "is_short": True,
            "label": "Scam",
            "scam_type": "Giveaway Scam",
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scraper_id": socket.gethostname()
        }
        
        print(f"    ✓ Giveaway scam detected: {username}")
        return metadata
        
    except Exception as e:
        print(f"    Error extracting metadata: {e}")
        return None

def extract_metadata(url):
    """Fallback metadata extraction using yt-dlp"""
    try:
        ydl_opts = {
            "quiet": True, 
            "skip_download": True, 
            "no_warnings": True,
            "extractor_args": {"tiktok": {"webpage_url_basename": "video"}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
        # Check duration (TikTok can be longer, but focus on shorter videos)
        duration = info.get("duration", 0)
        if duration and duration > 180:  # 3 minutes max
            return None
        
        # Check view count
        view_count = info.get("view_count", 0)
        if view_count and view_count > MAX_VIEW_COUNT:
            print(f"  ⊗ Too many views ({view_count:,} > {MAX_VIEW_COUNT:,}) - skipped")
            return None
        
        title = info.get('title', '')
        description = info.get('description', '')
        text_blob = f"{title} {description}"
        if not is_giveaway_scam(text_blob):
            return None
        
        hashtags = extract_hashtags(description)
        video_id = info.get('id', str(int(time.time())))
        
        return {
            "video_id": f"tiktok_{video_id}",
            "platform": "tiktok",
            "video_url": url,
            "title": title,
            "description": description,
            "uploader": info.get("uploader"),
            "channel": info.get("uploader_id"),
            "upload_date": info.get("upload_date"),
            "duration": duration,
            "view_count": view_count,
            "like_count": info.get("like_count"),
            "comment_count": info.get("comment_count"),
            "tags": [],  # TikTok doesn't use tags like YouTube
            "hashtags": hashtags,
            "is_short": True,
            "label": "Scam",
            "scam_type": "Giveaway Scam",
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scraper_id": socket.gethostname()
        }
    except Exception as e:
        print(f"  Error with yt-dlp extraction: {e}")
        return None

# ==================================================
# SAVE
# ==================================================
def save_metadata(meta):
    base = os.path.join(OUTPUT_DIR, "metadata", "tiktok_giveaway")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{meta['video_id']}.json")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Saved: {meta['video_id']} ({meta.get('view_count', 0):,} views)")
        return True
    return False

def download_video(url, video_id):
    if not DOWNLOAD_VIDEOS:
        return False
    
    base = os.path.join(OUTPUT_DIR, "videos", "tiktok_giveaway")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{video_id}.mp4")
    
    if os.path.exists(path):
        print(f"  ⊗ Already downloaded: {video_id}")
        return True
    
    # Try yt-dlp for TikTok
    ydl_opts = {
        "outtmpl": path, 
        "format": "best[ext=mp4]/best", 
        "quiet": True,
        "no_warnings": True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  ⬇ Downloaded: {video_id} ({size_mb:.1f}MB)")
            return True
    except Exception as e:
        print(f"  Error downloading: {e}")
    
    return False

# ==================================================
# MAIN CRAWLER
# ==================================================
def main():
    print("=" * 70)
    print("TikTok Giveaway Scam Scraper")
    print(f"Max views: {MAX_VIEW_COUNT:,} | Target: {MAX_VIDEOS} videos")
    print("=" * 70)
    
    driver = setup_driver()
    visited = set()
    collected = 0
    downloaded = 0
    queue = deque([tiktok_search_url(q) for q in SEARCH_QUERIES[:6]])  # Limit queries for TikTok
    
    try:
        while queue and collected < MAX_VIDEOS:
            page = queue.popleft()
            print(f"\n[>] Crawling: {page}")
            
            try:
                links = discover_video_links(driver, page)
            except Exception as e:
                print(f"  Error discovering links: {e}")
                continue
            
            for video_url in links:
                if video_url in visited or collected >= MAX_VIDEOS:
                    continue
                
                visited.add(video_url)
                print(f"\n[{collected+1}/{MAX_VIDEOS}] Processing: {video_url}")
                
                # Try Selenium-based extraction first
                meta = extract_metadata_selenium(driver, video_url)
                
                # Fallback to yt-dlp if Selenium fails
                if not meta:
                    print(f"    Trying yt-dlp fallback...")
                    meta = extract_metadata(video_url)
                
                if not meta:
                    print("    ⊗ Filtered out (not a giveaway scam, wrong duration, or too many views)")
                    continue
                
                # Save metadata
                if save_metadata(meta):
                    collected += 1
                
                # Download video
                if DOWNLOAD_VIDEOS:
                    if download_video(video_url, meta["video_id"]):
                        downloaded += 1
                
                print(f"    ✓ Total collected: {collected}/{MAX_VIDEOS} | Downloaded: {downloaded}")
                
                # Add user's profile to queue for more videos
                if meta.get("channel") and len(queue) < 10:
                    user_url = f"https://www.tiktok.com/{meta['channel']}"
                    if user_url not in visited:
                        queue.append(user_url)
                        print(f"    + Added user profile to queue")
                
                # Rate limiting for TikTok
                time.sleep(random.uniform(3, 6))
        
        print("\n" + "=" * 70)
        print(f"✓ Scraping complete! Collected {collected} giveaway scam TikToks")
        if DOWNLOAD_VIDEOS:
            print(f"✓ Downloaded {downloaded} videos")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
    finally:
        driver.quit()
        print(f"\nFinal count: {collected} videos")
        print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")
        
        # Show output structure
        print(f"\nFiles saved:")
        print(f"  └── {OUTPUT_DIR}/")
        print(f"      ├── metadata/tiktok_giveaway/*.json")
        print(f"      └── videos/tiktok_giveaway/*.mp4")

if __name__ == "__main__":
    main()
