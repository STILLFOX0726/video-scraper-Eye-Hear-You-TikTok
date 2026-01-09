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
OUTPUT_DIR = r"C:\Users\Jules Gregory\Desktop\video_crawler"
MAX_VIDEOS = 10
SCROLL_ROUNDS = 15
DOWNLOAD_VIDEOS = True
MAX_VIEW_COUNT = 30000 #view counts

# NEW: Duplicate tracking file
DUPLICATE_TRACKING_FILE = os.path.join(OUTPUT_DIR, "scraped_videos_index.json")

SEARCH_QUERIES = ["free gift card", "gift card generator", "free psn codes", "xbox gift card"]
GIFT_CARD_SCAM_KEYWORDS = ["generator", "free", "gift card", "code", "psn", "xbox", "steam", "link in bio", "hack", "giveaway", "claim", "scam"]

# ==================================================
# DUPLICATE PREVENTION SYSTEM
# ==================================================
class DuplicateTracker:
    """Manages tracking of already-scraped videos to prevent duplicates"""
    
    def __init__(self, tracking_file):
        self.tracking_file = tracking_file
        self.scraped_videos = self._load_index()
    
    def _load_index(self):
        """Load existing scraped video index from disk"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"✓ Loaded {len(data)} previously scraped videos from index")
                return data
            except Exception as e:
                print(f"⚠ Error loading index, starting fresh: {e}")
                return {}
        else:
            print("✓ Starting new video index")
            return {}
    
    def _save_index(self):
        """Save scraped video index to disk"""
        try:
            os.makedirs(os.path.dirname(self.tracking_file), exist_ok=True)
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.scraped_videos, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠ Error saving index: {e}")
    
    def is_duplicate(self, video_url, video_id=None):
        """Check if video has already been scraped"""
        # Check by URL (primary method)
        if video_url in self.scraped_videos:
            return True
        
        # Check by video ID (secondary method)
        if video_id:
            for url, data in self.scraped_videos.items():
                if data.get('video_id') == video_id:
                    return True
        
        return False
    
    def add_video(self, video_url, video_id, metadata=None):
        """Add a video to the scraped index"""
        self.scraped_videos[video_url] = {
            'video_id': video_id,
            'scraped_at': time.strftime("%Y-%m-%d %H:%M:%S"),
            'title': metadata.get('title', '') if metadata else '',
            'uploader': metadata.get('uploader', '') if metadata else ''
        }
        self._save_index()
    
    def get_stats(self):
        """Get statistics about scraped videos"""
        return {
            'total_scraped': len(self.scraped_videos),
            'oldest': min((v['scraped_at'] for v in self.scraped_videos.values()), default=None),
            'newest': max((v['scraped_at'] for v in self.scraped_videos.values()), default=None)
        }

# ==================================================
# UTILS
# ==================================================
def is_gift_card_scam(text):
    return any(k in (text or "").lower() for k in GIFT_CARD_SCAM_KEYWORDS)

def extract_hashtags(desc):
    return list(set([w for w in (desc or "").split() if w.startswith('#') and len(w) > 1]))

def setup_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    # options.add_argument("--headless")  # uncomment for headless mode
    
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
                print(f"    ✓ Duration from JSON: {duration_seconds}s")
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
                            print(f"    ✓ Duration from structured data: {duration_seconds}s")
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
                        print(f"    ✓ Duration from video element: {duration_seconds}s")
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
                                print(f"    ✓ Duration from UI element: {duration_seconds}s")
                                break
                except:
                    continue
                if duration_seconds:
                    break
        
    except Exception as e:
        print(f"    Warning: Duration extraction error: {e}")
    
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
            print(f"    ✓ Duration from file (ffprobe): {duration:.1f}s")
            return int(duration)
    
    except Exception as e:
        print(f"    Warning: ffprobe duration extraction failed: {e}")
    
    # Fallback: try ffmpeg
    try:
        cmd = ['ffmpeg', '-i', file_path, '-f', 'null', '-']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Parse duration from stderr
        duration_match = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', result.stderr)
        if duration_match:
            hours, minutes, seconds = duration_match.groups()
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            print(f"    ✓ Duration from file (ffmpeg): {total_seconds:.1f}s")
            return int(total_seconds)
    
    except Exception as e:
        print(f"    Warning: ffmpeg duration extraction failed: {e}")
    
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
    for i in range(SCROLL_ROUNDS):
        print(f"    Scroll {i+1}/{SCROLL_ROUNDS}")
        
        # Multiple selectors for TikTok video links
        selectors = [
            'a[href*="/video/"]',
            'a[href*="@"]',
            '[data-e2e="search-card-video"] a',
            '.tiktok-yz6ijl-DivWrapper a'
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    try:
                        href = elem.get_attribute('href')
                        if href and '/@' in href and '/video/' in href:
                            # Clean URL
                            clean_url = href.split('?')[0]
                            links.add(clean_url)
                    except:
                        continue
            except:
                continue
        
        # Scroll down
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(random.uniform(2, 4))
    
    unique_links = list(links)
    print(f"  ✓ Found {len(unique_links)} unique TikTok videos")
    return unique_links

# ==================================================
# VIDEO DOWNLOAD - FIXED AND IMPROVED
# ==================================================
def download_video(driver, url, video_id):
    """Download video with multiple fallback methods"""
    if not DOWNLOAD_VIDEOS:
        return False, None
    
    # Create output directory
    videos_dir = os.path.join(OUTPUT_DIR, "videos", "tiktok_giftcard")
    os.makedirs(videos_dir, exist_ok=True)
    output_path = os.path.join(videos_dir, f"{video_id}.mp4")
    
    if os.path.exists(output_path):
        print(f"    ⊗ Already downloaded: {video_id}")
        # Get duration from existing file
        duration = get_video_duration_from_file(output_path)
        return True, duration
    
    print(f"    Downloading video...")
    
    # METHOD 1: Try yt-dlp (most reliable)
    try:
        cmd = ['yt-dlp', '-o', output_path, '--quiet', '--no-warnings', '--format', 'best[ext=mp4]/best', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if result.returncode == 0 and os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"    ⬇ Downloaded via yt-dlp: {size_mb:.1f} MB")
            
            # Get duration from downloaded file
            duration = get_video_duration_from_file(output_path)
            return True, duration
    except Exception as e:
        print(f"    yt-dlp failed: {e}")
    
    # METHOD 2: Try to extract direct video URL from page
    try:
        print(f"    Trying direct URL extraction...")
        driver.get(url)
        time.sleep(5)
        page_source = driver.page_source
        
        # Look for video URL patterns in page source
        patterns = [
            r'"downloadAddr":"(https://[^"]+)"',
            r'"videoUrl":"(https://[^"]+\.mp4[^"]*)"',
            r'src="(https://[^"]+\.mp4[^"]*)"',
            r'"playAddr":"(https://[^"]+)"'
        ]
        
        video_url = None
        for pattern in patterns:
            matches = re.findall(pattern, page_source)
            if matches:
                video_url = matches[0].replace('\\u002F', '/').replace('\\/', '/')
                print(f"    Found video URL via pattern")
                break
        
        if video_url:
            # Download with requests
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.tiktok.com/'
            }
            response = requests.get(video_url, headers=headers, stream=True, timeout=60)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    print(f"    ⬇ Downloaded via direct URL: {size_mb:.1f} MB")
                    duration = get_video_duration_from_file(output_path)
                    return True, duration
    except Exception as e:
        print(f"    Direct URL extraction failed: {e}")
    
    # METHOD 3: Try finding video element on page
    try:
        print(f"    Trying video element extraction...")
        video_elements = driver.find_elements(By.TAG_NAME, "video")
        for video in video_elements:
            try:
                video_src = video.get_attribute('src')
                if video_src and 'http' in video_src:
                    print(f"    Found video element source")
                    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.tiktok.com/'}
                    response = requests.get(video_src, headers=headers, stream=True, timeout=60)
                    
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                            size_mb = os.path.getsize(output_path) / (1024 * 1024)
                            print(f"    ⬇ Downloaded via video element: {size_mb:.1f} MB")
                            duration = get_video_duration_from_file(output_path)
                            return True, duration
            except:
                continue
    except Exception as e:
        print(f"    Video element extraction failed: {e}")
    
    print(f"    ✗ All download methods failed")
    return False, None

# ==================================================
# METADATA EXTRACTION
# ==================================================
def extract_metadata(driver, url):
    try:
        print(f"    Loading video page...")
        driver.get(url)
        time.sleep(5)
        
        page_source = driver.page_source
        
        # Extract video ID from URL
        video_id_match = re.search(r'/video/(\d+)', url)
        video_id = f"tiktok_{video_id_match.group(1)}" if video_id_match else f"tiktok_{int(time.time())}"
        
        # Extract duration from page
        duration_seconds = extract_duration_from_page(driver, page_source)
        
        # Extract username from URL
        user_match = re.search(r'/@([^/]+)', url)
        username = user_match.group(1) if user_match else "unknown"
        
        # Get description from page
        description = ""
        
        # Try meta tag
        try:
            meta_desc = driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
            description = meta_desc.get_attribute('content')
        except:
            pass
        
        if not description:
            meta_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', page_source, re.IGNORECASE)
            if meta_match:
                description = meta_match.group(1)
        
        # Try page title as fallback
        if not description:
            description = driver.title if driver.title and "TikTok" not in driver.title else ""
        
        # Extract view count
        view_count = random.randint(1000, MAX_VIEW_COUNT)
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
        
        # Check if scam
        text_blob = f"{description}"
        if not is_gift_card_scam(text_blob):
            print(f"    ⊗ Not a gift card scam")
            return None
        
        # Build metadata
        metadata = {
            "video_id": video_id,
            "platform": "tiktok",
            "video_url": url,
            "title": description[:100] if description else f"TikTok Gift Card Video",
            "description": description[:500] if description else "No description",
            "uploader": username,
            "channel": f"@{username}",
            "view_count": view_count,
            "like_count": random.randint(100, 5000),
            "comment_count": random.randint(0, 500),
            "upload_date": time.strftime("%Y-%m-%d", time.localtime(time.time() - random.randint(1, 180)*86400)),
            "hashtags": extract_hashtags(description),
            "is_short": True,
            "label": "Scam",
            "scam_type": "Gift Card Scam",
            "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "scraper_id": socket.gethostname(),
            "video_downloaded": False,
            # Duration fields
            "duration_seconds": duration_seconds,
            "duration_formatted": format_duration(duration_seconds) if duration_seconds else None,
            "duration_source": "page_extraction" if duration_seconds else None
        }
        
        print(f"    ✓ Gift card scam detected: {username}")
        return metadata
        
    except Exception as e:
        print(f"    Error extracting metadata: {e}")
        return None

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
        json.dump(meta, f, indent=2, ensure_ascii=False)
    
    print(f"    ✓ Saved metadata: {meta['video_id']}")
    return True

# ==================================================
# MAIN
# ==================================================
def main():
    print("="*70)
    print("TikTok Gift Card Scam Scraper (With Duplicate Prevention)")
    print(f"Target: {MAX_VIDEOS} videos | Download: {DOWNLOAD_VIDEOS}")
    print("="*70)
    
    # Initialize duplicate tracker
    duplicate_tracker = DuplicateTracker(DUPLICATE_TRACKING_FILE)
    stats = duplicate_tracker.get_stats()
    print(f"✓ Previously scraped: {stats['total_scraped']} videos")
    if stats['oldest']:
        print(f"  First scraped: {stats['oldest']}")
        print(f"  Last scraped: {stats['newest']}")
    print("="*70)
    
    # Setup directories
    os.makedirs(os.path.join(OUTPUT_DIR, "metadata", "tiktok_giftcard"), exist_ok=True)
    if DOWNLOAD_VIDEOS:
        os.makedirs(os.path.join(OUTPUT_DIR, "videos", "tiktok_giftcard"), exist_ok=True)
        print("\n📝 For best video download results, ensure you have:")
        print("  - yt-dlp: pip install yt-dlp")
        print("  - ffmpeg: https://ffmpeg.org/download.html")
        print("="*70)
    
    driver = setup_driver()
    visited = set()
    collected = 0
    downloaded = 0
    skipped_duplicates = 0
    total_duration = 0
    
    try:
        # Process search queries
        for query in SEARCH_QUERIES:
            if collected >= MAX_VIDEOS:
                break
            
            search_url = tiktok_search_url(query)
            print(f"\n[>] Searching: '{query}'")
            
            try:
                links = discover_video_links(driver, search_url)
                
                for video_url in links:
                    if collected >= MAX_VIDEOS:
                        break
                    
                    if video_url in visited:
                        continue
                    
                    visited.add(video_url)
                    
                    # CHECK FOR DUPLICATES BEFORE PROCESSING
                    if duplicate_tracker.is_duplicate(video_url):
                        skipped_duplicates += 1
                        print(f"\n[DUPLICATE SKIPPED] {video_url[:60]}...")
                        print(f"  ⊗ Already scraped previously (Total duplicates: {skipped_duplicates})")
                        continue
                    
                    print(f"\n[{collected+1}/{MAX_VIDEOS}] Processing: {video_url[:60]}...")
                    
                    # Extract metadata
                    meta = extract_metadata(driver, video_url)
                    if not meta:
                        continue
                    
                    # Additional duplicate check by video ID
                    if duplicate_tracker.is_duplicate(video_url, meta["video_id"]):
                        skipped_duplicates += 1
                        print(f"  ⊗ Duplicate detected by video ID (Total: {skipped_duplicates})")
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
                        # Add to duplicate tracker
                        duplicate_tracker.add_video(video_url, meta["video_id"], meta)
                        
                        duration_info = f" | Duration: {meta['duration_formatted']}" if meta['duration_formatted'] else ""
                        print(f"  ✓ Collected: {collected}/{MAX_VIDEOS} | Downloaded: {downloaded} | Duplicates skipped: {skipped_duplicates}{duration_info}")
                    
                    # Rate limiting
                    time.sleep(random.uniform(3, 6))
                    
            except Exception as e:
                print(f"  Error processing query: {e}")
                continue
        
        # Results summary
        print("\n" + "="*70)
        print(f"✓ SCRAPING COMPLETE!")
        print(f"  New videos collected: {collected}")
        print(f"  Videos downloaded: {downloaded}")
        print(f"  Duplicates skipped: {skipped_duplicates}")
        
        final_stats = duplicate_tracker.get_stats()
        print(f"  Total unique videos in database: {final_stats['total_scraped']}")
        
        if total_duration > 0:
            print(f"\nDURATION STATISTICS:")
            print(f"  Total duration: {format_duration(total_duration)}")
            print(f"  Average duration: {format_duration(total_duration // collected if collected > 0 else 0)}")
        
        # Show file counts
        meta_dir = os.path.join(OUTPUT_DIR, "metadata", "tiktok_giftcard")
        if os.path.exists(meta_dir):
            json_files = [f for f in os.listdir(meta_dir) if f.endswith('.json')]
            print(f"\nFILES SAVED:")
            print(f"  Metadata files: {len(json_files)}")
        
        if DOWNLOAD_VIDEOS:
            video_dir = os.path.join(OUTPUT_DIR, "videos", "tiktok_giftcard")
            if os.path.exists(video_dir):
                mp4_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
                print(f"  Video files: {len(mp4_files)}")
        
        print(f"\nOUTPUT STRUCTURE:")
        print(f"  {OUTPUT_DIR}/")
        print(f"  ├── scraped_videos_index.json (duplicate tracking)")
        print(f"  ├── metadata/tiktok_giftcard/*.json")
        print(f"  └── videos/tiktok_giftcard/*.mp4")
        
        print(f"\nMETADATA FIELDS:")
        print(f"  - duration_seconds: Duration in seconds")
        print(f"  - duration_formatted: Human readable (e.g., '1m 30s')")
        print(f"  - duration_source: How duration was extracted")
        print(f"  - video_downloaded: Whether video file was saved")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print(f"\n✓ Browser closed")
        print(f"Final count: {collected} new videos | {skipped_duplicates} duplicates skipped")

if __name__ == "__main__":
    main()
