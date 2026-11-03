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
    """Renvoie la liste des flux sous forme de dicts {url, hashtag, count}.

    Formats acceptés dans config.yaml :
      - rss_url: "https://..."            (ancien format, un seul flux)
      - feeds:
          - "https://..."                  (hashtag par défaut, 1 item)
          - url: "https://..."
            hashtag: "#MonHashtag"         (hashtag propre au flux)
            count: 3                       (nombre d'items récents à publier)
    """
    raw = CONFIG.get("feeds")
    if raw is None and "rss_url" in CONFIG:
        raw = [CONFIG["rss_url"]]
    if not raw:
        raise SystemExit("Aucun flux RSS configuré (clé 'feeds' ou 'rss_url').")

    feeds = []
    for item in raw:
        if isinstance(item, str):
            feeds.append({"url": item, "hashtag": DEFAULT_HASHTAG, "count": 1})
        else:
            count = item.get("count", 1)
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                raise SystemExit(
                    f"'count' invalide pour {item['url']} : {count!r} "
                    "(entier >= 1 attendu)."
                )
            feeds.append({
                "url": item["url"],
                "hashtag": item.get("hashtag", DEFAULT_HASHTAG),
                "count": count,
            })
    return feeds


# Script
def load_cache(feeds):
    """Cache : {url_du_flux: [ids_publiés]}.

    Une valeur chaîne (ancien format : dernier id publié) est conservée
    telle quelle et interprétée par published_ids().
    """
    if not os.path.exists(CACHE_FILE):
        return {}
    with open(CACHE_FILE, "r") as f:
        data = json.load(f)
    # Migration de l'ancien format {"last_id": ...} (un seul flux)
    if "last_id" in data and len(data) == 1:
        return {feeds[0]["url"]: data["last_id"]} if feeds else {}
    return data


def published_ids(cached, entries):
    """Ensemble des ids déjà publiés parmi entries (du plus récent au plus ancien)."""
    if cached is None:
        return set()
    if isinstance(cached, str):
        # Ancien format : seul le dernier id publié est connu. On considère
        # cet article et tous les plus anciens comme déjà publiés.
        ids = [e.get("id", e.link) for e in entries]
        if cached in ids:
            return set(ids[ids.index(cached):])
        return {cached}
    return set(cached)


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
        count = feed_conf["count"]

        try:
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                print(f"[{rss_url}] Aucun article trouvé")
                continue

            all_ids = [e.get("id", e.link) for e in feed.entries]
            done = published_ids(cache.get(rss_url), feed.entries)

            # Les `count` items les plus récents non encore publiés,
            # publiés du plus ancien au plus récent pour garder l'ordre
            # chronologique sur la timeline.
            todo = [
                (e, eid)
                for e, eid in zip(feed.entries[:count], all_ids[:count])
                if eid not in done
            ]
            todo.reverse()

            if not todo:
                print(f"[{rss_url}] Déjà publié")
                continue

            if client is None:
                client = Client()
                client.login(BLUESKY_HANDLE, BLUESKY_PASSWORD)

            for entry, entry_id in todo:
                text, facets = build_post(entry, hashtag)
                client.send_post(text=text, facets=facets)
                done.add(entry_id)
                # On ne garde que les ids encore présents dans le flux
                # pour que le cache ne grossisse pas indéfiniment.
                cache[rss_url] = [i for i in all_ids if i in done]
                save_cache(cache)
                print(f"[{rss_url}] Publié :", entry.title)
        except Exception as e:
            print(f"[{rss_url}] Erreur : {e}")


if __name__ == "__main__":
    main()
