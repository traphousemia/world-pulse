#!/usr/bin/env python3
"""
Zero-LLM news sweep for World Pulse.

Pulls directly from official primary-source RSS/Atom feeds (ReliefWeb disaster
reports, USGS significant earthquakes) and maintains a credited link roundup
in news/manifest.json, rendered on /articles.html. No AI text generation, no
fabricated facts, no API/token cost -- pure deterministic feed parsing.

It deliberately does NOT generate a page per feed item. A fixed template can
only produce near-identical pages, which is scaled content abuse under Google's
spam policies; feed items are summarised and linked to the primary source
instead. Original articles on this site are written by hand.

Run via GitHub Actions on a daily cron. Safe to run repeatedly: it dedupes
against news/manifest.json by source URL and caps how many items it adds.
"""
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

REPO_ROOT = __file__.rsplit('/scripts/', 1)[0]
MANIFEST_PATH = f"{REPO_ROOT}/news/manifest.json"

MAX_NEW_ITEMS_PER_RUN = 2
# One item per feed per run, so a high-volume feed can't monopolise the list.
MAX_PER_FEED_PER_RUN = 1
MAX_SUMMARY_CHARS = 280
# Keep the roundup recent; older entries drop off rather than accumulating.
MAX_MANIFEST_ITEMS = 40

FEEDS = [
    {
        "name": "WHO — Disease Outbreak News",
        "url": "https://www.who.int/feeds/entity/csr/don/en/rss.xml",
        "kind": "rss",
        "tag": "Disease Outbreak",
    },
    {
        "name": "ReliefWeb — Epidemics",
        "url": "https://reliefweb.int/disasters/rss.xml?search=type.name.exact:%22Epidemic%22",
        "kind": "rss",
        "tag": "Disease Outbreak",
    },
    {
        "name": "ReliefWeb — Famine & Food Insecurity",
        "url": "https://reliefweb.int/disasters/rss.xml?search=type.name.exact:%22Food%20Insecurity%22",
        "kind": "rss",
        "tag": "Humanitarian",
    },
    {
        "name": "USGS — Significant Earthquakes",
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.atom",
        "kind": "atom",
        "tag": "Natural Disaster",
    },
]

# Title substrings that indicate a reference document/appeal rather than an
# actual news event -- skip these even if they slip through a feed filter.
NON_NEWS_TITLE_MARKERS = (
    "reference handbook", "annual report", "guidelines", "toolkit",
    "factsheet", "fact sheet", "training manual", "standard operating",
)


def looks_like_real_news(title):
    lowered = title.lower()
    return not any(marker in lowered for marker in NON_NEWS_TITLE_MARKERS)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "WorldPulseNewsSweep/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def strip_html(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text, n):
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",.;: ") + "…"


def usgs_clean_summary(title):
    """USGS feed descriptions are technical PAGER/ShakeMap codes, not prose.
    Build a clean sentence straight from the title instead, e.g.
    'M 6.3 - south of the Kermadec Islands' -> a plain sentence."""
    m = re.match(r"M\s*([\d.]+)\s*-\s*(.+)", title)
    if not m:
        return None
    magnitude, place = m.group(1), m.group(2).strip()
    return f"A magnitude {magnitude} earthquake struck {place}, per USGS."




def parse_rss(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = strip_html(item.findtext("description") or "")
        pub = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "description": desc, "pubDate": pub})
    return items


ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


def parse_atom(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for entry in root.findall("a:entry", ATOM_NS):
        title = (entry.findtext("a:title", default="", namespaces=ATOM_NS) or "").strip()
        link_el = entry.find("a:link[@rel='alternate']", ATOM_NS) or entry.find("a:link", ATOM_NS)
        link = link_el.get("href") if link_el is not None else ""
        desc = strip_html(entry.findtext("a:summary", default="", namespaces=ATOM_NS) or "")
        updated = (entry.findtext("a:updated", default="", namespaces=ATOM_NS) or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "description": desc, "pubDate": updated})
    return items


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:70]


def load_manifest():
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def already_covered(manifest, source_link):
    for entry in manifest:
        for s in entry.get("sources", []):
            if s.get("url") == source_link:
                return True
    return False



def main():
    manifest = load_manifest()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    published_this_run = 0
    new_entries = []

    for feed in FEEDS:
        if published_this_run >= MAX_NEW_ITEMS_PER_RUN:
            break
        taken_from_this_feed = 0
        try:
            raw = fetch(feed["url"])
            items = parse_rss(raw) if feed["kind"] == "rss" else parse_atom(raw)
        except Exception as e:
            print(f"WARN: failed to fetch {feed['name']}: {e}", file=sys.stderr)
            continue

        for item in items:
            if published_this_run >= MAX_NEW_ITEMS_PER_RUN:
                break
            if taken_from_this_feed >= MAX_PER_FEED_PER_RUN:
                break
            if already_covered(manifest, item["link"]):
                continue
            if not looks_like_real_news(item["title"]):
                continue

            if feed["kind"] == "atom":  # USGS: build from title, ignore noisy PAGER text
                cleaned = usgs_clean_summary(item["title"])
                if not cleaned:
                    continue
                summary = cleaned
            else:
                if not item["description"]:
                    continue
                summary = truncate(item["description"], MAX_SUMMARY_CHARS)
            slug = f"{today}-{slugify(item['title'])}"
            if any(e.get("slug") == slug for e in manifest) or any(e.get("slug") == slug for e in new_entries):
                continue

            # No `url` key: this is a credited feed summary, not an article we
            # wrote. articles.html links the headline straight to the source.
            entry = {
                "slug": slug,
                "title": item["title"],
                "date": today,
                "summary": summary,
                "sources": [{"name": feed["name"], "url": item["link"]}],
            }
            new_entries.append(entry)
            published_this_run += 1
            taken_from_this_feed += 1
            print(f"Listed: {item['title']}")

    if not new_entries:
        print("No new items to publish this run.")
        return

    manifest = (new_entries + manifest)[:MAX_MANIFEST_ITEMS]
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Nothing is added to sitemap.xml: these entries have no page of their own,
    # they render on /articles.html and link out to the primary source.
    print(f"Done. Listed {len(new_entries)} new item(s) on /articles.html.")


if __name__ == "__main__":
    main()
