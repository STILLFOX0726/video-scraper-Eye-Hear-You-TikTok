📌 How to Use This TikTok Video Scraper Repo

This guide assumes the scripts are standard Python web scrapers that fetch TikTok data using Selenium or similar tools. If your code differs, adjust accordingly.

✅ 1. Clone the Repository
git clone https://github.com/STILLFOX0726/video-scraper-Eye-Hear-You-TikTok.git
cd video-scraper-Eye-Hear-You-TikTok

✅ 2. Create and Activate a Python Virtual Environment

macOS / Linux:

python3 -m venv .venv
source .venv/bin/activate


Windows:

python -m venv .venv
.\.venv\Scripts\activate

✅ 3. Install Dependencies

If there is a requirements.txt, install them:

pip install -r requirements.txt


If not, you likely need:

pip install selenium yt-dlp webdriver-manager


(These are typical for video scrapers — adjust if your scripts use different packages.) 
GitHub

✅ 4. Set Up WebDriver (Selenium)

If the scripts use Selenium, you need a WebDriver (ChromeDriver for Chrome).

Install ChromeDriver automatically:

If your script uses webdriver-manager, it may handle this automatically.

Otherwise:

macOS Homebrew:

brew install chromedriver


Or download from the official site.

✅ 5. Configure Each Script

Open a script like video_scrape_crypto.py in VS Code and check for settings at the top:

Examples of things to configure:

SEARCH_QUERIES = ["keyword1", "keyword2"]
OUTPUT_DIR = "/path/to/save/videos"
MAX_VIDEOS = 50


Make sure you set:

TikTok search terms or target username/hashtag

Output directory

Optional filters

✅ 6. Run the Scrapers

Run each script like this:

python video_scrape_crypto.py
python video_scrape_giftcard.py
python video_scrape_giveaway.py

🧠 What Each Script Likely Does

Although there’s no visible README, the file names suggest:

🔹 video_scrape_crypto.py
— Scrapes TikTok videos related to crypto scams

🔹 video_scrape_giftcard.py
— Scrapes gift-card or promo-related TikTok content

🔹 video_scrape_giveaway.py
— Scrapes giveaway-style videos

These scripts probably extract:

Video links or metadata

Maybe downloads videos

Saves results to JSON, CSV, or a local folder

This pattern is similar to other scrapers in GitHub repos you have seen. 
GitHub

🧹 Good Practices

✅ Add a .gitignore file
Include:

.venv/
__pycache__/
*.json
*.mp4
*.db
