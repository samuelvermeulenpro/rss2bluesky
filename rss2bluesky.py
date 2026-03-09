import os
import json
import feedparser
import yaml
from atproto import Client, models

# Répertoire du script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration YAML
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.yaml")
with open(CONFIG_PATH, "r") as f:
    CONFIG = yaml.safe_load(f)

RSS_URL = CONFIG["rss_url"]
BLUESKY_HANDLE = CONFIG["bluesky"]["handle"]
BLUESKY_PASSWORD = CONFIG["bluesky"]["password"]
POST_HASHTAG = CONFIG["post"]["hashtag"]
CACHE_FILE = os.path.join(SCRIPT_DIR, CONFIG["cache"]["file"])

# Script
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {"last_id": None}
    with open(CACHE_FILE, "r") as f:
        return json.load(f)


def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def create_facets(text, url, hashtag):
    facets = []

    # Facet pour le lien
    start_url = text.index(url)
    end_url = start_url + len(url)

    facets.append(
        models.AppBskyRichtextFacet.Main(
            index=models.AppBskyRichtextFacet.ByteSlice(
                byteStart=start_url,
                byteEnd=end_url
            ),
            features=[
                models.AppBskyRichtextFacet.Link(uri=url)
            ]
        )
    )

    # Facet pour le hashtag
    if hashtag in text:
        start_tag = text.index(hashtag)
        end_tag = start_tag + len(hashtag)

        facets.append(
            models.AppBskyRichtextFacet.Main(
                index=models.AppBskyRichtextFacet.ByteSlice(
                    byteStart=start_tag,
                    byteEnd=end_tag
                ),
                features=[
                    models.AppBskyRichtextFacet.Tag(
                        tag=hashtag.lstrip("#")
                    )
                ]
            )
        )

    return facets

def main():
    cache = load_cache()

    feed = feedparser.parse(RSS_URL)
    entry = feed.entries[0]

    entry_id = entry.get("id", entry.link)

    if entry_id == cache["last_id"]:
        print("Déjà publié")
        return

    title = entry.title
    url = entry.link

    text = f"{POST_HASHTAG} - {title} à lire sur\n{url}"

    facets = create_facets(text, url, POST_HASHTAG)

    client = Client()
    client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

    client.send_post(
        text=text,
        facets=facets
    )

    cache["last_id"] = entry_id
    save_cache(cache)

    print("Publié :", title)


if __name__ == "__main__":
    main()