import os
import time
import logging
import re
import requests
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")
SOURCE_DIR = os.getenv("SOURCE_DIR")
MOVIE_DIR = os.getenv("MOVIE_DIR")
TV_SHOW_DIR = os.getenv("TV_SHOW_DIR")
VIDEO_EXTENSIONS = ['.mkv', '.mp4', '.avi', '.mov']

# Basic Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# --- TMDb API Functions ---
def search_media(title):
    """Searches TMDb for a movie or TV show."""
    if not API_KEY or API_KEY == "your_api_key_here":
        logging.error("TMDb API key is not configured. Please set it in the .env file.")
        return None
    url = f"https://api.themoviedb.org/3/search/multi?api_key={API_KEY}&query={title}"
    try:
        response = requests.get(url)
        response.raise_for_for_status()
        return response.json().get('results', [])
    except requests.RequestException as e:
        logging.error(f"Error searching TMDb: {e}")
        return None

def get_movie_details(movie_id):
    """Gets details for a specific movie."""
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error getting movie details: {e}")
        return None

def get_tv_show_details(tv_id, season, episode):
    """Gets details for a specific TV show episode."""
    url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season}/episode/{episode}?api_key={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        # It's possible the episode doesn't exist, so we log a warning, not an error.
        logging.warning(f"Could not get TV show details for S{season}E{episode}: {e}")
        return None

# --- Helper Functions ---
def parse_filename(filename):
    """Parses a filename to extract title, year, season, and episode."""
    filename = filename.lower()
    # Regex for SxxExx pattern
    season_episode = re.search(r'[sS](\d{1,2})[eE](\d{1,2})', filename)
    if season_episode:
        season = int(season_episode.group(1))
        episode = int(season_episode.group(2))
        # Assume the text before the season/episode is the title
        title = re.split(r'[sS]\d{1,2}[eE]\d{1,2}', filename)[0].replace('.', ' ').strip()
        return {'title': title, 'season': season, 'episode': episode}

    # Regex for year pattern (for movies)
    year = re.search(r'\(?(\d{4})\)?', filename)
    if year:
        year_val = year.group(1)
        # Assume the text before the year is the title
        title = re.split(r'\(?\d{4}\)?', filename)[0].replace('.', ' ').strip()
        return {'title': title, 'year': year_val}

    # If no patterns match, return the whole filename as title
    return {'title': filename.replace('.', ' ').strip()}

def clean_name(name):
    """Removes illegal characters from a filename."""
    return re.sub(r'[<>:"/\\|?*]', '', name)

# --- File Processing Logic ---
def process_file(file_path):
    """
    Processes a new video file: identifies, renames, and moves it.
    """
    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1]

    if file_ext not in VIDEO_EXTENSIONS:
        logging.info(f"Skipping non-video file: {filename}")
        return

    logging.info(f"Processing video file: {filename}")
    parsed_info = parse_filename(os.path.splitext(filename)[0])
    
    if not parsed_info or not parsed_info.get('title'):
        logging.warning(f"Could not parse title from: {filename}")
        return

    search_results = search_media(parsed_info['title'])
    if not search_results:
        logging.warning(f"No search results for: {parsed_info['title']}")
        return

    # Find the best match (usually the first result)
    media = search_results[0]
    media_type = media.get('media_type')

    if media_type == 'movie':
        movie_details = get_movie_details(media['id'])
        if movie_details:
            title = clean_name(movie_details['title'])
            year = movie_details['release_date'][:4]
            new_filename = f"{title}-{year}{file_ext}"
            dest_path = os.path.join(MOVIE_DIR, new_filename)
            
            logging.info(f"Renaming and moving movie: {filename} -> {dest_path}")
            shutil.move(file_path, dest_path)

    elif media_type == 'tv':
        if 'season' in parsed_info and 'episode' in parsed_info:
            show_details = get_tv_show_details(media['id'], parsed_info['season'], parsed_info['episode'])
            if show_details:
                show_name = clean_name(media['name'])
                season_num = str(show_details['season_number']).zfill(2)
                episode_num = str(show_details['episode_number']).zfill(2)
                year = show_details['air_date'][:4]
                
                new_filename = f"{show_name}.s{season_num}e{episode_num}-{year}{file_ext}"
                
                season_folder = os.path.join(TV_SHOW_DIR, show_name, f"Season {season_num}")
                os.makedirs(season_folder, exist_ok=True)
                dest_path = os.path.join(season_folder, new_filename)

                logging.info(f"Renaming and moving TV show: {filename} -> {dest_path}")
                shutil.move(file_path, dest_path)
        else:
            logging.warning(f"Could not determine season/episode for TV show: {filename}")

# --- Directory Monitoring ---
class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        """
        Called when a file or directory is created.
        """
        if not event.is_directory:
            # Wait a moment for the file to be fully written
            time.sleep(5)
            process_file(event.src_path)

def start_monitoring():
    """
    Starts monitoring the source directory for new files.
    """
    if not all([API_KEY, SOURCE_DIR, MOVIE_DIR, TV_SHOW_DIR]):
        logging.error("Missing environment variables. Please check your .env file.")
        return
    
    # Create destination directories if they don't exist
    os.makedirs(MOVIE_DIR, exist_ok=True)
    os.makedirs(TV_SHOW_DIR, exist_ok=True)

    logging.info(f"Starting to monitor directory: {SOURCE_DIR}")
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, SOURCE_DIR, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Observer stopped.")
    observer.join()

# --- Main Execution ---
if __name__ == "__main__":
    start_monitoring()
