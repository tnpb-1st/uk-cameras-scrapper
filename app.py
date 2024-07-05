import csv
import logging
import os
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from flask import Flask, jsonify

app = Flask(__name__)

load_dotenv()

video_urls = {}
csv_filename = os.getenv('CSV_FILENAME')
base_save_path = os.getenv('VIDEOS_BASE_PATH')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("video_scraping.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def ensure_directory_exists(path):
    os.makedirs(path, exist_ok=True)


def download_video(url, filename, save_path, current_time):
    response = requests.get(f"{url}?time={current_time}", stream=True)
    video_path = os.path.join(save_path, filename)
    with open(video_path, 'wb') as video_file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                video_file.write(chunk)
    logger.info(f"Downloaded video: {filename} from URL: {url} at {current_time}")


def scrape_videos():
    now = datetime.now(timezone.utc).astimezone(timezone(offset=timedelta(hours=-3)))
    date_str = now.strftime("%d-%m-%Y")
    time_str = now.strftime("%H-%M-%S")

    for name, url in video_urls.items():
        subfolder_path = os.path.join(base_save_path, name, date_str)
        ensure_directory_exists(subfolder_path)
        filename = f"{time_str}.mp4"
        download_video(url, filename, subfolder_path, now)


def update_video_urls_from_csv(csv_file):
    global video_urls
    video_urls = {}
    with open(csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            key = f"camera{row['Id']}"
            video_urls[key] = row['Url']
    logger.info("Updated video URLs from CSV")


def get_time_in_ticks(current_datetime):
    # The base date in the Gregorian calendar
    base_date = datetime(1, 1, 1, tzinfo=timezone.utc)

    # Calculate the difference in seconds
    delta = current_datetime - base_date
    seconds = delta.total_seconds()

    # Number of ticks in one second
    ticks_per_second = 10_000_000

    # Convert seconds to ticks
    ticks = int(seconds * ticks_per_second)

    return ticks


update_video_urls_from_csv(csv_filename)


scheduler = BackgroundScheduler()
scheduler.add_job(scrape_videos, 'interval', minutes=20)
scheduler.start()


@app.route('/')
def index():
    return jsonify({"message": "Video scraping service is running!"})


if __name__ == "__main__":
    app.run(debug=True)
