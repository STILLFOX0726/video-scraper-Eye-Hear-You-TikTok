TikTok Scam Video Scraper – Eye Hear You 

A Python-based web scraping tool designed to identify and collect TikTok videos that exhibit characteristics of common scam types, including crypto scams, gift card generator scams, and fake giveaways.

This project is intended for research, academic, and educational purposes, particularly in the study of online scam patterns on short-form video platforms.

Features

🔍 Multi-category scam detection: Crypto, gift card generators, and giveaway scams
🎯 Keyword-based filtering: Scam-related terms and patterns
📊 Metadata extraction: Video URL, title, description, uploader, engagement data
💾 Optional video downloading: Save matching TikTok videos locally
🔄 Automated browsing: Selenium-driven TikTok exploration
📝 Structured data output: JSON / CSV (depending on configuration)
🖥️ Windows-optimized paths and setup

Scam Categories
1. Crypto Scams (video_scrape_crypto.py)

Targets TikTok videos promoting:

Free Bitcoin or cryptocurrency giveaways

Crypto “doublers” or generators

Celebrity impersonation scams

Guaranteed profit or investment schemes

Fake airdrops, mining, or staking offers

2. Gift Card Scams (video_scrape_giftcard.py)

Targets TikTok videos promoting:

Free gift card generators (Steam, PSN, Xbox, Google Play, etc.)

Unlimited or “working” code generators

Fake redemption websites

Exploit or hack claims

3. Giveaway Scams (video_scrape_giveaway.py)

Targets TikTok videos promoting:

Free iPhone, PS5, or electronics giveaways

Cash giveaways (PayPal, CashApp, GCash, etc.)

“Guaranteed winner” claims

Fake influencer-hosted giveaways

Prerequisites

Python 3.8 or higher

Google Chrome browser

Windows OS (paths and configuration are Windows-specific)

Git installed

Installation
1. Clone the Repository
git clone https://github.com/STILLFOX0726/video-scraper-Eye-Hear-You-TikTok.git
cd video-scraper-Eye-Hear-You-TikTok

2. Create and Activate a Virtual Environment (Windows)
python -m venv .venv
.venv\Scripts\activate


You should see:

(.venv)

3. Install Required Dependencies

If requirements.txt exists:

pip install -r requirements.txt


If not, install manually:

pip install selenium yt-dlp webdriver-manager


Required packages:

selenium – browser automation

yt-dlp – video metadata and downloading

webdriver-manager – automatic ChromeDriver management

Configuration

Each script contains configurable parameters near the top of the file.

Example:

OUTPUT_DIR = r"C:\Users\YourUsername\Desktop\tiktok_scraper"
MAX_VIDEOS = 50
DOWNLOAD_VIDEOS = True

Common Configuration Options
Variable	Description
OUTPUT_DIR	Directory where data/videos are saved
MAX_VIDEOS	Maximum number of videos to collect
DOWNLOAD_VIDEOS	Enable or disable video downloads
SEARCH_QUERIES	Scam-related keywords or hashtags
Recommended Settings
For Testing
MAX_VIDEOS = 5–10
DOWNLOAD_VIDEOS = True

For Large Data Collection
MAX_VIDEOS = 500–2000
DOWNLOAD_VIDEOS = True  # Requires significant storage

Usage
Running a Scraper

Execute any of the following:

# Crypto scam scraper
python video_scrape_crypto.py

# Gift card scam scraper
python video_scrape_giftcard.py

# Giveaway scam scraper
python video_scrape_giveaway.py

What Happens During Execution

Chrome Browser Launch: Selenium opens an automated Chrome window

Search Execution: Runs predefined TikTok search queries

Video Discovery: Collects video URLs from results

Metadata Extraction: Captures video and uploader information

Filtering: Applies keyword-based scam detection

Data Saving: Stores metadata locally

Video Download: (Optional) Saves TikTok videos

Output Structure (Typical)
video_scraper/
├── metadata/
│   ├── tiktok_crypto/
│   │   ├── tiktok_VIDEO_ID_1.json
│   │   └── tiktok_VIDEO_ID_2.json
│   ├── tiktok_giftcard/
│   └── tiktok_giveaway/
└── videos/
    ├── tiktok_crypto/
    ├── tiktok_giftcard/
    └── tiktok_giveaway/

Metadata JSON Format (Example)
{
  "video_id": "tiktok_ABC123",
  "platform": "tiktok",
  "video_url": "https://www.tiktok.com/@user/video/ABC123",
  "title": "Free Crypto Giveaway",
  "description": "Limited time offer...",
  "uploader": "ChannelName",
  "upload_date": "20240115",
  "view_count": 25000,
  "like_count": 1200,
  "comment_count": 300,
  "hashtags": ["#crypto", "#giveaway"],
  "label": "Scam",
  "scam_type": "Crypto Scam",
  "scraped_at": "2024-01-15 14:30:00"
}

Customization
Adding Custom Search Queries
SEARCH_QUERIES = [
    "free crypto tiktok",
    "gift card generator",
    "giveaway legit"
]

Running in Headless Mode

Uncomment in the Selenium setup:

options.add_argument("--headless")

Interrupting Execution

Press Ctrl + C to stop the scraper safely.
The script will:

Close Chrome

Preserve collected data

Display summary statistics

Troubleshooting
ChromeDriver Issues

Automatically handled by webdriver-manager

Ensure Chrome is up to date

Rate Limiting

Reduce scraping speed

Add delays (e.g., time.sleep(3–7))

Memory Issues

Reduce MAX_VIDEOS

Disable video downloads

Ethical Considerations

⚠️ Important Notice

For research and educational use only

Respect TikTok’s Terms of Service

Avoid aggressive scraping

Do not harass or target creators

Manual review is strongly recommended

Legal Disclaimer

This tool is provided as-is for educational and research purposes only.
Users are responsible for compliance with:

TikTok Terms of Service

Copyright laws

Data protection regulations

Local web scraping laws

The authors assume no liability for misuse.

Future Improvements

Multi-platform support (YouTube Shorts, Instagram Reels)

Machine learning–based scam classification

Database integration (MongoDB / PostgreSQL)

Web dashboard for visualization

Proxy support

Resume functionality

Contributing

Contributions are welcome:

Fork the repository

Create a feature branch

Commit your changes

Submit a pull request

License

MIT License – see the LICENSE file for details.

Contact

For questions, issues, or collaboration:

Open an issue on GitHub

Email: your.email@example.com

Disclaimer

This tool identifies potential scam content based on keyword patterns.
Not all flagged videos are fraudulent. Manual validation is required.
