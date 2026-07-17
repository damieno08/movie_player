import os
import json
import requests
from PIL import Image
from io import BytesIO

# ==========================
# CONFIG
# ==========================

API_KEY = "06bd3064c2776d249aa6df7789acee15"
MOVIES_DIR = r"E:\Movies"

# Video extensions to scan for the "filename" field
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".m4v", ".flv"}

SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
DETAILS_URL = "https://api.themoviedb.org/3/movie/{movie_id}"
CREDITS_URL = "https://api.themoviedb.org/3/movie/{movie_id}/credits"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/original"


def get_movie_info(title):
    """Search TMDb for a movie and return its metadata."""

    search = requests.get(
        SEARCH_URL,
        params={
            "api_key": API_KEY,
            "query": title
        }
    ).json()

    if not search.get("results"):
        return None

    movie = search["results"][0]
    movie_id = movie["id"]

    details = requests.get(
        DETAILS_URL.format(movie_id=movie_id),
        params={"api_key": API_KEY}
    ).json()

    credits = requests.get(
        CREDITS_URL.format(movie_id=movie_id),
        params={"api_key": API_KEY}
    ).json()

    return {
        "runtime": details.get("runtime", 0),
        "description": details.get("overview", ""),
        "genres": [g["name"] for g in details.get("genres", [])],
        "cast": [c["name"] for c in credits.get("cast", [])[:10]],
        "poster": details.get("poster_path")
    }


def download_cover(poster_path, save_path):
    """Download the poster image from TMDb."""

    if not poster_path:
        return False

    url = POSTER_BASE_URL + poster_path

    response = requests.get(url)
    if response.status_code != 200:
        return False

    image = Image.open(BytesIO(response.content))
    image.save(save_path, "PNG")

    return True


def main():

    # Gather all subdirectories
    folders = [
        os.path.join(MOVIES_DIR, f)
        for f in os.listdir(MOVIES_DIR)
        if os.path.isdir(os.path.join(MOVIES_DIR, f))
    ]

    for folder in folders:
        folder_name = os.path.basename(folder)
        config_path = os.path.join(folder, "config.txt")

        # 1. ONLY look for folders without the config file
        if os.path.exists(config_path):
            print(f"Skipping '{folder_name}' (config already exists)")
            continue

        # 2. Find the actual video file inside the folder for the "filename" key
        actual_video_filename = None
        for item in os.listdir(folder):
            _, ext = os.path.splitext(item)
            if ext.lower() in VIDEO_EXTENSIONS:
                actual_video_filename = item
                break

        if not actual_video_filename:
            print(f"Skipping '{folder_name}' (no video file found inside to map)")
            continue

        # 3. Title comes strictly from the folder name
        title = folder_name
        print(f"Looking up '{title}' on TMDb...")

        info = get_movie_info(title)

        if info is None:
            print(f" ✗ Could not find '{title}' on TMDb")
            continue

        # 4. Construct the dictionary exactly matching your example format
        movie_data = {
            "title": title,
            "cover": f"{title}.png",
            "runtime": info["runtime"],
            "description": info["description"],
            "genres": info["genres"],
            "cast": info["cast"],
            "filename": actual_video_filename
        }

        cover_path = os.path.join(folder, movie_data["cover"])

        # Try to download the cover art
        if download_cover(info["poster"], cover_path):
            print("  ✓ Cover downloaded")
        else:
            print("  ✗ No cover found")

        # 5. Save the fresh config.txt file
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(movie_data, f, indent=4, ensure_ascii=False)

        print("  ✓ Config created\n")

    print("Done!")


if __name__ == "__main__":
    main()