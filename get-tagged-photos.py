import argparse, sys, os, time, wget, json, ssl, urllib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime

def start_session():
    print("Opening Browser...")
    wd_options = Options()
    wd_options.add_argument("--disable-notifications")
    wd_options.add_argument("--disable-infobars")
    wd_options.add_argument("--mute-audio")
    wd_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=wd_options)

    driver.get("https://www.facebook.com/")

    print("\n" + "=" * 60)
    print("ACTION REQUIRED:")
    print("1. Log in to Facebook in the Chrome window.")
    print("2. Complete any CAPTCHA/2FA checks manually.")
    print("3. Once you see your feed, return here.")
    print("=" * 60 + "\n")

    input("---> Press ENTER in this terminal after you are fully logged in... ")
    return driver

def get_main_photo_url(driver):
    """Finds the main high-res photo in Facebook's modern lightbox view."""
    imgs = driver.find_elements(By.TAG_NAME, "img")
    candidate_urls = []
    
    for img in imgs:
        try:
            src = img.get_attribute("src") or ""
            if ("scontent" in src or "fbcdn" in src) and not any(thumb in src for thumb in ["p50x50", "p160x160", "p320x320", "s480x480"]):
                width = img.size.get('width', 0)
                height = img.size.get('height', 0)
                if width > 250 or height > 250:
                    candidate_urls.append((width * height, src))
        except Exception:
            continue

    if candidate_urls:
        candidate_urls.sort(key=lambda x: x[0], reverse=True)
        return candidate_urls[0][1]
    return None

def index_photos(driver):
    print("\nNavigating to your tagged photos...")
    driver.get("https://www.facebook.com/me/photos_of")
    time.sleep(4)

    print("=" * 60)
    print("ACTION REQUIRED:")
    print("Click on the FIRST photo thumbnail on the page to open the photo viewer.")
    print("=" * 60)
    input("---> Press ENTER after you have opened the first photo... ")

    data = {'tagged': []}
    seen_fb_urls = set()
    
    consecutive_duplicates = 0
    MAX_CONSECUTIVE_DUPLICATES = 5  # Stop automatically after 5 already-indexed photos in a row

    print("\nStarting indexing...")

    while True:
        time.sleep(2)
        current_fb_url = driver.current_url

        if current_fb_url not in seen_fb_urls:
            media_url = get_main_photo_url(driver)

            if media_url:
                seen_fb_urls.add(current_fb_url)
                consecutive_duplicates = 0  # Reset counter on new photo

                doc = {
                    'fb_url': current_fb_url,
                    'fb_date': datetime.today().strftime('%Y-%m-%d'),
                    'fb_caption': 'Facebook Photo',
                    'fb_tags': '',
                    'media_url': media_url,
                    'media_type': 'image',
                    'user_name': 'Facebook User',
                    'user_url': ''
                }

                data['tagged'].append(doc)
                print(f"{len(data['tagged'])}) Found photo: {current_fb_url}")

                with open('tagged.json', 'w') as f:
                    json.dump(data, f, indent=4)
            else:
                consecutive_duplicates += 1
        else:
            consecutive_duplicates += 1
            print(f"Skipping already-indexed photo ({consecutive_duplicates}/{MAX_CONSECUTIVE_DUPLICATES})...")

        # Circuit breaker: exit when looping starts
        if consecutive_duplicates >= MAX_CONSECUTIVE_DUPLICATES:
            print(f"\nReached {MAX_CONSECUTIVE_DUPLICATES} consecutive duplicates. All photos indexed!")
            break

        # Move to next photo
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ARROW_RIGHT)
        except Exception:
            break

def download_photos():
    ssl._create_default_https_context = ssl._create_unverified_context
    folder = 'photos/'
    if not os.path.exists(folder):
        os.makedirs(folder)

    if not os.path.exists('tagged.json'):
        print("tagged.json not found. Run indexing first.")
        return

    with open('tagged.json') as json_file:
        data = json.load(json_file)

    if not data.get('tagged'):
        print("No photos found in tagged.json to download.")
        return

    print(f"\nSaving {len(data['tagged'])} photos to {folder}...")

    for i, d in enumerate(data['tagged']):
        if d['media_type'] == 'image':
            filename_date = d.get('fb_date', datetime.today().strftime('%Y-%m-%d'))
            
            try:
                img_id = d['media_url'].split('?')[0].split('/')[-1].split('_')[1]
            except Exception:
                img_id = str(i + 1)

            new_filename = os.path.join(folder, f"{filename_date}_{img_id}.jpg")

            if os.path.exists(new_filename):
                print(f"Already Exists (Skipping): {new_filename}")
                continue

            delay = 1
            while True:
                try:
                    print(f"Downloading photo {i+1} of {len(data['tagged'])}...")
                    wget.download(d['media_url'], new_filename, False)
                    print(f" Saved -> {new_filename}")
                    break
                except (TimeoutError, urllib.error.URLError, Exception):
                    print(f"Download failed, retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    if delay > 8:
                        print("Failed to download image. Skipping.")
                        break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Facebook Scraper')
    parser.add_argument('--download', action='store_true', help='Download photos only')
    args = parser.parse_args()

    try:
        if args.download:
            download_photos()
        else:
            driver = start_session()
            index_photos(driver)
            download_photos()
            driver.quit()
    except KeyboardInterrupt:
        print('\nScript stopped by user.')
