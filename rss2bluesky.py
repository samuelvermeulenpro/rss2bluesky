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

BLUESKY_HANDLE = CONFIG["bluesky"]["handle"]
BLUESKY_PASSWORD = CONFIG["bluesky"]["password"]
DEFAULT_HASHTAG = CONFIG.get("post", {}).get("hashtag", "")
CACHE_FILE = os.path.join(SCRIPT_DIR, CONFIG["cache"]["file"])


def load_feeds():
    """Renvoie la liste des flux sous forme de dicts {url, hashtag}.

    Formats acceptés dans config.yaml :
      - rss_url: "https://..."            (ancien format, un seul flux)
      - feeds:
          - "https://..."                  (hashtag par défaut)
          - url: "https://..."
            hashtag: "#MonHashtag"         (hashtag propre au flux)
    """
    raw = CONFIG.get("feeds")
    if raw is None and "rss_url" in CONFIG:
        raw = [CONFIG["rss_url"]]
    if not raw:
        raise SystemExit("Aucun flux RSS configuré (clé 'feeds' ou 'rss_url').")

    feeds = []
    for item in raw:
        if isinstance(item, str):
            feeds.append({"url": item, "hashtag": DEFAULT_HASHTAG})
        else:
            feeds.append({
                "url": item["url"],
                "hashtag": item.get("hashtag", DEFAULT_HASHTAG),
            })
    return feeds


# Script
def load_cache(feeds):
    """Cache : {url_du_flux: dernier_id_publié}."""
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        data = json.load(f)
    # Migration de l'ancien format {"last_id": ...} (un seul flux)
    if "last_id" in data and len(data) == 1:
        return {feeds[0]["url"]: data["last_id"]} if feeds else {}
    return data


def save_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def byte_slice(text, substring):
    """Renvoie (byteStart, byteEnd) de substring dans text.

    Bluesky attend des positions en octets UTF-8, pas en caractères :
    un caractère accentué (é, à...) occupe 2 octets.
    """
    start = len(text[:text.index(substring)].encode("utf-8"))
    return start, start + len(substring.encode("utf-8"))


def create_facets(text, url, hashtag):
    facets = []

    # Facet pour le lien
    start_url, end_url = byte_slice(text, url)

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
    if hashtag and hashtag in text:
        start_tag, end_tag = byte_slice(text, hashtag)

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

def build_post(entry, hashtag):
    title = entry.title
    url = entry.link
    if hashtag:
        text = f"{hashtag} - {title} à lire sur\n{url}"
    else:
        text = f"{title} à lire sur\n{url}"
    return text, create_facets(text, url, hashtag)


def main():
    feeds = load_feeds()
    cache = load_cache(feeds)
    client = None

    for feed_conf in feeds:
        rss_url = feed_conf["url"]
        hashtag = feed_conf["hashtag"]

        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                print(f"[{rss_url}] Aucun article trouvé")
                continue

            entry = feed.entries[0]
            entry_id = entry.get("id", entry.link)

            if entry_id == cache.get(rss_url):
                print(f"[{rss_url}] Déjà publié")
                continue

            text, facets = build_post(entry, hashtag)

            if client is None:
                client = Client()
                client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

            client.send_post(text=text, facets=facets)

            cache[rss_url] = entry_id
            save_cache(cache)

            print(f"[{rss_url}] Publié :", entry.title)
        except Exception as e:
            print(f"[{rss_url}] Erreur : {e}")


if __name__ == "__main__":
    main()
