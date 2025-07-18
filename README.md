# Media Organizer

This script monitors a directory for new video files, identifies them as either a movie or a TV show using the TMDb API, renames them to a clean format, and moves them to their respective destination folders.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Get a TMDb API Key:**
    *   Create an account on [The Movie Database (TMDb)](https://www.themoviedb.org/).
    *   Go to your account settings, find the "API" section, and request an API key.

3.  **Configure the Environment:**
    *   Rename the `.env.example` file to `.env`.
    *   Open the `.env` file and add your TMDb API key and define your source and destination directories.

    ```
    TMDB_API_KEY="your_api_key_here"
    SOURCE_DIR="/path/to/your/downloads"
    MOVIE_DIR="/path/to/your/movies"
    TV_SHOW_DIR="/path/to/your/tv_shows"
    ```

## Usage

Run the script from your terminal:

```bash
python media_organizer.py
```

The script will start monitoring the `SOURCE_DIR` for new video files and process them automatically.
