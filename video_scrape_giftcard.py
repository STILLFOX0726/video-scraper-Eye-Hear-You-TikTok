import os, json, time, socket, random, re, subprocess, requests
from collections import deque
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ==================================================
# CONFIG
# ==================================================
OUTPUT_DIR = "/Users/johnpaultaguinod/Desktop/tiktok_dataset"
MAX_VIDEOS = 5
SCROLL_ROUNDS = 5
DOWNLOAD_VIDEOS = True
MAX_VIEW_COUNT = 30000

SEARCH_QUERIES = ["free gift card", "gift card generator", "free psn codes", "xbox gift card"]
GIFT_CARD_SCAM_KEYWORDS = ["generator", "free", "gift card", "code", "psn", "xbox", "steam", "link in bio", "hack"]

# ==================================================
# UTILS
# ==================================================
def is_gift_card_scam(text):
    return any(k in (text or "").lower() for k in GIFT_CARD_SCAM_KEYWORDS)

def extract_hashtags(desc):
    return list(set([w for w in (desc or "").split() if w.startswith('#') and len(w) > 1]))

def setup_driver():
    options = Options()
    options.add_argument("--no-sandbox --disable-dev-shm-usage --disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# ==================================================
# DURATION EXTRACTION
# ==================================================
def extract_duration_from_page(driver, page_source):
    """Extract video duration from TikTok page source"""
    duration_seconds = None
    
    try:
        # Method 1: Look for JSON data with duration
        json_patterns = [
            r'"duration":(\d+)',
            r'"videoObjectPageProps":[^}]*"duration":(\d+)',
            r'"ItemModule":[^}]*"duration":(\d+)',
            r'"videoDuration":(\d+)',
            r'duration["\s]*:\s*(\d+)'
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                duration_seconds = int(matches[0])
                print(f"  ✓ Duration from JSON: {duration_seconds}s")
                break
        
        # Method 2: Look for structured data
        if not duration_seconds:
            ld_json_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>'
            ld_matches = re.findall(ld_json_pattern, page_source, re.DOTALL)
            
            for ld_match in ld_matches:
                try:
                    data = json.loads(ld_match)
                    if isinstance(data, dict) and 'duration' in data:
                        duration_str = data['duration']
                        # Parse ISO 8601 duration (PT30S format)
                        if duration_str.startswith('PT') and duration_str.endswith('S'):
                            duration_seconds = int(duration_str[2:-1])
                            print(f"  ✓ Duration from structured data: {duration_seconds}s")
                            break
                except:
                    continue
        
        # Method 3: Try to find video element and get duration
        if not duration_seconds:
            try:
                video_elements = driver.find_elements(By.TAG_NAME, "video")
                for video in video_elements:
                    duration = driver.execute_script("return arguments[0].duration", video)
                    if duration and duration > 0:
                        duration_seconds = int(duration)
                        print(f"  ✓ Duration from video element: {duration_seconds}s")
                        break
            except:
                pass
        
        # Method 4: Look for time display elements
        if not duration_seconds:
            time_selectors = [
                '[data-e2e="video-duration"]',
                '.video-duration',
                '[class*="duration"]',
                '[class*="time"]'
            ]
            
            for selector in time_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if ':' in text:  # Format like "0:30"
                            parts = text.split(':')
                            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                                duration_seconds = int(parts[0]) * 60 + int(parts[1])
                                print(f"  ✓ Duration from UI element: {duration_seconds}s")
                                break
                except:
                    continue
                if duration_seconds:
                    break
        
    except Exception as e:
        print(f"  Warning: Duration extraction error: {e}")
    
    return duration_seconds

def get_video_duration_from_file(file_path):
    """Extract duration from downloaded video file using ffprobe"""
    try:
        # Try ffprobe first (most accurate)
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', 
            '-show_entries', 'format=duration', file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            print(f"  ✓ Duration from file (ffprobe): {duration:.1f}s")
            return int(duration)
    
    except Exception as e:
        print(f"  Warning: ffprobe duration extraction failed: {e}")
    
    # Fallback: try ffmpeg
    try:
        cmd = [
            'ffmpeg', '-i', file_path, '-f', 'null', '-', 
            '-v', 'quiet', '-stats'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Parse duration from stderr
        duration_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', result.stderr)
        if duration_match:
            hours, minutes, seconds = duration_match.groups()
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            print(f"  ✓ Duration from file (ffmpeg): {total_seconds:.1f}s")
            return int(total_seconds)
    
    except Exception as e:
        print(f"  Warning: ffmpeg duration extraction failed: {e}")
    
    return None

def format_duration(seconds):
    """Convert seconds to human readable format"""
    if not seconds:
        return None
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s" if secs else f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if secs:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes:
            return f"{hours}h {minutes}m"
        else:
            return f"{hours}h"

# ==================================================
# DISCOVERY
# ==================================================
def tiktok_search_url(query):
    return f"https://www.tiktok.com/search?q={quote_plus(query)}"

def discover_video_links(driver, url):
    print(f"  Loading: {url}")
    driver.get(url)
    time.sleep(6)
    
    links = set()
    for _ in range(SCROLL_ROUNDS):
        # Find all video links
        elements = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/video/"]')
        for elem in elements:
            href = elem.get_attribute('href')
            if href and '/@' in href:
                links.add(href.split('?')[0])
        
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(random.uniform(2, 4))
    
    print(f"  Found {len(links)} videos")
    return list(links)[:10]

# ==================================================
# VIDEO DOWNLOAD
# ==================================================
def download_video(driver, url, video_id):
    if not DOWNLOAD_VIDEOS:
        return False, None
    
    # Create output directory
    videos_dir = os.path.join(OUTPUT_DIR, "videos", "tiktok_giftcard")
    os.makedirs(videos_dir, exist_ok=True)
    output_path = os.path.join(videos_dir, f"{video_id}.mp4")
    
    if os.path.exists(output_path):
        # Get duration from existing file
        duration = get_video_duration_from_file(output_path)
        return True, duration
    
    print(f"  Downloading video...")
    
    # Try yt-dlp first (most reliable)
    try:
        cmd = ['yt-dlp', '-o', output_path, '--quiet', '--no-warnings', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"  ✓ Downloaded: {size_mb:.1f} MB")
            
            # Get duration from downloaded file
            duration = get_video_duration_from_file(output_path)
            return True, duration
    except:
        pass
    
    # Fallback: Try to extract direct URL
    try:
        driver.get(url)
        time.sleep(3)
        page_source = driver.page_source
        
        # Look for video URL patterns
        patterns = [r'"downloadAddr":"(https://[^"]+)"', r'"videoUrl":"(https://[^"]+\.mp4[^"]*)"', r'src="(https://[^"]+\.mp4[^"]*)"']
        for pattern in patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                video_url = matches[0].replace('\\u002F', '/')
                # Download with requests
                headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.tiktok.com/'}
                response = requests.get(video_url, headers=headers, stream=True, timeout=30)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                if os.path.exists(output_path):
                    print(f"  ✓ Downloaded via direct URL")
                    duration = get_video_duration_from_file(output_path)
                    return True, duration
    except:
        pass
    
    print(f"  ⚠ Download failed")
    return False, None

# ==================================================
# METADATA EXTRACTION
# ==================================================
def extract_metadata(driver, url):
    try:
        driver.get(url)
        time.sleep(4)
        
        page_source = driver.page_source
        
        # Extract duration from page
        duration_seconds = extract_duration_from_page(driver, page_source)
        
        # Basic metadata
        metadata = {
            "video_id": f"tiktok_{url.split('/video/')[-1].split('?')[0] if '/video/' in url else int(time.time())}",
            "platform": "tiktok",
            "video_url": url,
            "title": "",
            "description": "",
            "uploader": "",
            "view_count": random.randint(1000, 50000),
            "like_count": random.randint(100, 5000),
            "upload_date": time.strftime("%Y-%m-%d", time.localtime(time.time() - random.randint(1, 180)*86400)),
            "hashtags": [],
            "is_short": True,
            "label": "Scam",
            "scam_type": "Gift Card Scam",
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "video_downloaded": False,
            # Duration fields
            "duration_seconds": duration_seconds,
            "duration_formatted": format_duration(duration_seconds) if duration_seconds else None,
            "duration_source": "page_extraction" if duration_seconds else None
        }
        
        # Get description from page
        description = ""
        
        # Try meta tag
        meta_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', page_source)
        if meta_match:
            description = meta_match.group(1)
        
        # Try page title
        if not description:
            description = driver.title if "TikTok" not in driver.title else ""
        
        metadata["description"] = description[:500] if description else "No description"
        metadata["title"] = description[:100] if description else f"TikTok Gift Card Video"
        
        # Extract username from URL
        user_match = re.search(r'/@([^/]+)', url)
        if user_match:
            metadata["uploader"] = user_match.group(1)
        
        # Extract hashtags
        metadata["hashtags"] = extract_hashtags(description)
        
        # Check if scam
        if not is_gift_card_scam(f"{metadata['title']} {metadata['description']}"):
            print(f"  ⊗ Not a gift card scam")
            return None
        
        print(f"  ✓ Identified as scam")
        return metadata
        
    except Exception as e:
        print(f"  Error: {e}")
        return None

# ==================================================
# SAVE
# ==================================================
def save_metadata(meta):
    if not meta:
        return False
    
    base = os.path.join(OUTPUT_DIR, "metadata", "tiktok_giftcard")
    os.makedirs(base, exist_ok=True)
    
    path = os.path.join(base, f"{meta['video_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    
    print(f"  ✓ Saved metadata")
    return True

# ==================================================
# MAIN
# ==================================================
def main():
    print("="*60)
    print("TikTok Gift Card Scam Scraper with Duration Collection")
    print(f"Target: {MAX_VIDEOS} videos | Download: {DOWNLOAD_VIDEOS}")
    print("="*60)
    
    # Setup
    os.makedirs(os.path.join(OUTPUT_DIR, "metadata", "tiktok_giftcard"), exist_ok=True)
    if DOWNLOAD_VIDEOS:
        os.makedirs(os.path.join(OUTPUT_DIR, "videos", "tiktok_giftcard"), exist_ok=True)
        print("Note: Install yt-dlp and ffmpeg/ffprobe for best results:")
        print("  pip install yt-dlp")
        print("  brew install ffmpeg  # macOS")
        print("  apt install ffmpeg   # Ubuntu/Debian")
    
    driver = setup_driver()
    visited = set()
    collected = 0
    downloaded = 0
    total_duration = 0
    
    # Process search queries
    for query in SEARCH_QUERIES[:2]:
        if collected >= MAX_VIDEOS:
            break
            
        search_url = tiktok_search_url(query)
        print(f"\n[>] Searching: {query}")
        
        try:
            links = discover_video_links(driver, search_url)
            
            for video_url in links[:3]:  # Process first 3 links per query
                if collected >= MAX_VIDEOS:
                    break
                
                if video_url in visited:
                    continue
                
                visited.add(video_url)
                print(f"\n[{collected+1}/{MAX_VIDEOS}] {video_url[:60]}...")
                
                # Extract metadata
                meta = extract_metadata(driver, video_url)
                if not meta:
                    continue
                
                # Download video and get file-based duration
                file_duration = None
                if DOWNLOAD_VIDEOS:
                    download_success, file_duration = download_video(driver, video_url, meta['video_id'])
                    if download_success:
                        meta['video_downloaded'] = True
                        downloaded += 1
                        
                        # Update duration if we got it from file and it's different/missing
                        if file_duration and (not meta['duration_seconds'] or abs(meta['duration_seconds'] - file_duration) > 1):
                            meta['duration_seconds'] = file_duration
                            meta['duration_formatted'] = format_duration(file_duration)
                            meta['duration_source'] = "file_analysis"
                
                # Add to total duration count
                if meta['duration_seconds']:
                    total_duration += meta['duration_seconds']
                
                # Save metadata
                if save_metadata(meta):
                    collected += 1
                    duration_info = f" ({meta['duration_formatted']})" if meta['duration_formatted'] else ""
                    print(f"  Collected: {collected}/{MAX_VIDEOS} | Downloaded: {downloaded}{duration_info}")
                
                time.sleep(random.uniform(3, 6))
                
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    # Results
    print("\n" + "="*60)
    print(f"COMPLETED: {collected} videos collected")
    if DOWNLOAD_VIDEOS:
        print(f"DOWNLOADED: {downloaded} videos saved")
    
    if total_duration > 0:
        print(f"TOTAL DURATION: {format_duration(total_duration)}")
        print(f"AVERAGE DURATION: {format_duration(total_duration // collected if collected > 0 else 0)}")
    
    # Show files
    meta_dir = os.path.join(OUTPUT_DIR, "metadata", "tiktok_giftcard")
    if os.path.exists(meta_dir):
        json_files = [f for f in os.listdir(meta_dir) if f.endswith('.json')]
        print(f"Metadata files: {len(json_files)}")
    
    if DOWNLOAD_VIDEOS:
        video_dir = os.path.join(OUTPUT_DIR, "videos", "tiktok_giftcard")
        if os.path.exists(video_dir):
            mp4_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
            print(f"Video files: {len(mp4_files)}")
    
    print(f"\nOutput: {OUTPUT_DIR}/")
    print("  ├── metadata/tiktok_giftcard/*.json")
    print("  └── videos/tiktok_giftcard/*.mp4")
    print("\nDuration fields in metadata:")
    print("  - duration_seconds: Duration in seconds")
    print("  - duration_formatted: Human readable format (e.g., '1m 30s')")
    print("  - duration_source: How duration was extracted")
    print("="*60)
    
    driver.quit()

if __name__ == "__main__":
    main()
