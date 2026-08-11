import argparse, sys, os, time, wget, json, piexif, ssl, urllib.request, urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateutil.parser import parse
from datetime import datetime, timedelta

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

def get_photo_location(driver):
    """Extracts place tags (location) associated with the open photo."""
    try:
        place_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/places/') or contains(@href, 'facebook.com/places')]")
        for link in place_links:
            text = link.text.strip()
            if text:
                return text
    except Exception:
        pass
    return ""

def geocode_location(location_str):
    """Converts a location string (e.g. 'Paris, France') into Lat/Lon using Nominatim."""
    if not location_str:
        return None, None
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(location_str)}&format=json&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'FBPhotoDownloader/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f" (Geocoding error for '{location_str}': {e})")
    return None, None

def change_to_rational(number):
    """Converts float lat/lon into EXIF GPS rational format."""
    f = abs(number)
    d = int(f)
    m = int((f - d) * 60)
    s = round((f - d - (m / 60.0)) * 3600.0 * 100.0)
    return ((d, 1), (m, 1), (s, 100))

def get_gps_exif(lat, lon):
    """Generates EXIF GPS dictionary."""
    lat_ref = 'N' if lat >= 0 else 'S'
    lon_ref = 'E' if lon >= 0 else 'W'
    return {
        piexif.GPSIFD.GPSLatitudeRef: lat_ref,
        piexif.GPSIFD.GPSLatitude: change_to_rational(lat),
        piexif.GPSIFD.GPSLongitudeRef: lon_ref,
        piexif.GPSIFD.GPSLongitude: change_to_rational(lon)
    }

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
    MAX_CONSECUTIVE_DUPLICATES = 5  # Stop after 5 already-indexed photos in a row

    print("\nStarting indexing...")

    while True:
        time.sleep(2)
        current_fb_url = driver.current_url

        if current_fb_url not in seen_fb_urls:
            media_url = get_main_photo_url(driver)
            location_text = get_photo_location(driver)

            if media_url:
                seen_fb_urls.add(current_fb_url)
                consecutive_duplicates = 0  # Reset circuit breaker on finding a new photo

                doc = {
                    'fb_url': current_fb_url,
                    'fb_date': datetime.today().strftime('%Y-%m-%d'),
                    'fb_location': location_text,
                    'fb_caption': 'Facebook Photo',
                    'fb_tags': '',
                    'media_url': media_url,
                    'media_type': 'image',
                    'user_name': 'Facebook User',
                    'user_url': ''
                }

                data['tagged'].append(doc)
                loc_str = f" [Location: {location_text}]" if location_text else ""
                print(f"{len(data['tagged'])}) Found photo{loc_str}: {current_fb_url}")

                with open('tagged.json', 'w') as f:
                    json.dump(data, f, indent=4)
            else:
                consecutive_duplicates += 1
        else:
            consecutive_duplicates += 1
            print(f"Skipping already-indexed photo ({consecutive_duplicates}/{MAX_CONSECUTIVE_DUPLICATES})...")

        # Stop indexing if we hit the consecutive duplicate limit
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
                    break
                except (TimeoutError, urllib.error.URLError, Exception):
                    print(f"Download failed, retrying in {delay}s...")
                    time.sleep(delay)
                    delay *= 2
                    if delay > 8:
                        print("Failed to download image. Skipping.")
                        break

            # Embed EXIF Data (Date, Description, and GPS Location)
            try:
                exif_dict = piexif.load(new_filename)
                exif_date = datetime.today().strftime("%Y:%m:%d %H:%M:%S")
                img_desc = d.get('fb_caption', '') + '\n' + d.get('fb_tags', '')

                exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = exif_date
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = img_desc.encode('utf-8')

                # Handle Geocoding & GPS metadata
                location_name = d.get('fb_location')
                if location_name:
                    lat, lon = geocode_location(location_name)
                    if lat is not None and lon is not None:
                        gps_dict = get_gps_exif(lat, lon)
                        exif_dict['GPS'] = gps_dict
                        print(f" -> Geotagged at {location_name} ({lat}, {lon})")

                piexif.insert(piexif.dump(exif_dict), new_filename)
            except Exception as e:
                print(f" Skipped EXIF writing: {e}")

            print(f" Saved -> {new_filename}")

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
