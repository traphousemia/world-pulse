#!/usr/bin/env python3
"""
Zero-LLM news sweep for World Pulse.

Pulls directly from official primary-source RSS/Atom feeds (ReliefWeb disaster
reports, USGS significant earthquakes) and publishes short, clearly-attributed
excerpts linking back to the original report. No AI text generation, no
fabricated facts, no API/token cost -- pure deterministic feed parsing.

Run via GitHub Actions on a daily cron. Safe to run repeatedly: it dedupes
against news/manifest.json by source URL and caps how many new items it
publishes per run.
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
SITEMAP_PATH = f"{REPO_ROOT}/sitemap.xml"
NEWS_DIR = f"{REPO_ROOT}/news"
TEMPLATE_PATH = f"{NEWS_DIR}/2026-08-04-drc-ebola-outbreak.html"

MAX_NEW_ITEMS_PER_RUN = 2
MAX_SUMMARY_CHARS = 280

FEEDS = [
    {
        "name": "ReliefWeb — Epidemics",
        "url": "https://reliefweb.int/disasters/rss.xml?search=type.name.exact:%22Epidemic%22",
        "kind": "rss",
        "tag": "Disease Outbreak",
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


def usgs_body_paragraphs(title):
    """Return a list of HTML paragraph strings providing factual context
    for a USGS earthquake article. Uses only well-established seismological
    facts — no fabricated details about the specific event."""
    m = re.match(r"M\s*([\d.]+)\s*-\s*(.+)", title)
    if not m:
        return []
    magnitude, place = m.group(1), m.group(2).strip()
    place_esc = html.escape(place)
    try:
        mag_f = float(magnitude)
    except ValueError:
        mag_f = 0.0

    if mag_f >= 7.0:
        severity = "major"
        damage_desc = "capable of causing severe to violent shaking and serious damage over wide areas, with potential for casualties in populated regions"
    elif mag_f >= 6.0:
        severity = "strong"
        damage_desc = "capable of causing moderate to heavy damage to poorly constructed buildings, and light to moderate damage to well-built structures"
    else:
        severity = "moderate"
        damage_desc = "generally felt widely but causing only minor damage to well-constructed structures"

    paragraphs = [
        f"<h2>What Happened</h2>",
        f"<p>A magnitude {html.escape(magnitude)} earthquake — classified as <strong>{severity}</strong> on the USGS moment magnitude scale — struck {place_esc} and was recorded by global seismic monitoring networks. The event was added to the USGS Significant Earthquakes catalog, which tracks seismic events of M5.0 or greater that have the potential to cause damage, trigger tsunamis, or generate public concern.</p>",
        "<h2>Understanding the Magnitude</h2>",
        f"<p>A <strong>magnitude {html.escape(magnitude)}</strong> earthquake is {damage_desc}. Each full point increase on the moment magnitude scale represents roughly 32 times more energy released — meaning a M{html.escape(magnitude)} event releases significantly more energy than smaller earthquakes that occur routinely. The USGS tracks thousands of earthquakes globally every day, but only those meeting the significant threshold are included in this feed.</p>",
        "<h2>Global Earthquake Context</h2>",
        "<p>Earthquakes are among the most unpredictable contributors to sudden mass-casualty events worldwide. The Earth experiences approximately 13,000 earthquakes of M4.0 or greater each year — about 35 per day. Of those, roughly 130 reach M6.0 or above. Major earthquakes of M7.0 or greater average about 15 per year globally. Historically, earthquakes have caused an estimated 2.3 million deaths over the past century, predominantly in densely populated, geologically vulnerable regions of Asia, the Middle East, and Latin America.</p>",
        "<p>Seismic activity near coastlines or submarine fault zones is also monitored for tsunami potential by the Pacific Tsunami Warning Center and regional agencies. Following any significant offshore earthquake, warning centers evaluate depth, focal mechanism, and seafloor displacement to determine whether a wave advisory is warranted.</p>",
        "<h2>Seismic Activity and World Population</h2>",
        '<p>Natural disasters including earthquakes contribute to global mortality statistics tracked in real time on <a href="/index.html">World Pulse</a>. Our <a href="/world-death-toll-causes-of-death.html">world death toll breakdown</a> covers how natural disasters, infectious disease, and other causes intersect with global population trends. For more on how births and deaths shape the world population count, see our guide to <a href="/birth-rate-vs-death-rate.html">birth rates vs. death rates</a>.</p>',
    ]
    return paragraphs


def reliefweb_body_paragraphs(title, summary):
    """Return a list of HTML paragraph strings providing factual context
    for a ReliefWeb disease outbreak article."""
    title_esc = html.escape(title)
    summary_esc = html.escape(summary)
    paragraphs = [
        "<h2>Event Summary</h2>",
        f"<p>{summary_esc}</p>",
        "<h2>About Disease Outbreak Reporting</h2>",
        "<p>ReliefWeb, operated by the United Nations Office for the Coordination of Humanitarian Affairs (OCHA), is one of the world's primary humanitarian information services. Its disaster and epidemic feeds aggregate situation reports, flash updates, and outbreak notifications from WHO, CDC, Médecins Sans Frontières, and government health ministries. Events listed in the Epidemics category meet a threshold of public health significance — they are not routine illness clusters but confirmed outbreaks requiring coordinated response.</p>",
        "<h2>Disease Outbreaks and Global Mortality</h2>",
        "<p>Infectious disease remains one of the largest contributors to global mortality. According to WHO data, communicable diseases collectively account for roughly 13–15 million deaths per year worldwide — about one in four deaths globally. Respiratory infections, diarrheal diseases, tuberculosis, malaria, and emerging pathogens all contribute to this toll. Outbreak events like the one reported here represent acute spikes above the endemic baseline, often straining local health systems and requiring international assistance.</p>",
        '<p>World Pulse tracks deaths from all causes in real time on the <a href="/index.html">live world death toll counter</a>. For context on what is driving the global death toll today, see our <a href="/world-death-toll-causes-of-death.html">breakdown of deaths by cause</a> — updated continuously using World Bank and WHO data.</p>',
    ]
    return paragraphs


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


def build_article_html(template, title, tag, date_str, summary, source_name, source_url, canonical_slug, extra_paragraphs=None):
    """Rebuilds the article page line-by-line from the fixed template, replacing
    only known head/meta/JSON-LD lines and the <main> body. Uses plain string
    matching (no regex substitution with dynamic replacement text) so that
    backslashes, quotes, or any other characters in scraped feed text can
    never be misinterpreted as regex syntax."""
    title_full = f"{title} — World Pulse"
    title_esc = html.escape(title, quote=True)
    title_full_esc = html.escape(title_full, quote=True)
    desc_esc = html.escape(summary, quote=True)
    canonical_url = f"https://worldpulse.fyi/news/{canonical_slug}.html"
    date_label = datetime.strptime(date_str, "%Y-%m-%d").strftime("%B %-d, %Y")

    body_content = []
    if extra_paragraphs:
        body_content.extend(["  " + p for p in extra_paragraphs])
        body_content.append("")
    else:
        body_content.append(f"  <p>{html.escape(summary)}</p>")
        body_content.append("")

    new_body = body_content + [
        '  <div class="sources">',
        "    <h2>Source</h2>",
        "    <ol>",
        f'      <li><a href="{html.escape(source_url, quote=True)}" target="_blank" rel="noopener">{html.escape(source_name)} — full report</a></li>',
        "    </ol>",
        "  </div>",
        "",
        '  <div class="related">',
        "    <h2>Related reading</h2>",
        "    <ul>",
        '      <li><a href="/world-death-toll-causes-of-death.html">World Death Toll Today: What\'s Actually Killing People, By the Numbers</a></li>',
        '      <li><a href="/articles.html">More recent news</a></li>',
        "    </ul>",
        "  </div>",
    ]

    lines = template.split("\n")
    out_lines = []
    in_head_section = True
    skip_until_main_close = False

    for line in lines:
        stripped = line.strip()

        if skip_until_main_close:
            if stripped == "</main>":
                skip_until_main_close = False
                out_lines.append(line)
            continue

        if stripped.startswith("<title>") and in_head_section:
            out_lines.append(f"<title>{title_full_esc}</title>")
        elif stripped.startswith('<meta name="description" content="'):
            out_lines.append(f'<meta name="description" content="{desc_esc}">')
        elif stripped.startswith('<meta name="keywords" content="'):
            out_lines.append(f'<meta name="keywords" content="{html.escape(tag.lower())}, world population news, world death toll news, {html.escape(title_esc.lower())}">')
        elif stripped.startswith('<meta property="og:title" content="'):
            out_lines.append(f'<meta property="og:title" content="{title_full_esc}">')
        elif stripped.startswith('<meta property="og:description" content="'):
            out_lines.append(f'<meta property="og:description" content="{desc_esc}">')
        elif stripped.startswith('<meta property="og:url" content="'):
            out_lines.append(f'<meta property="og:url" content="{canonical_url}">')
        elif stripped.startswith('<meta name="twitter:title" content="'):
            out_lines.append(f'<meta name="twitter:title" content="{title_full_esc}">')
        elif stripped.startswith('<meta name="twitter:description" content="'):
            out_lines.append(f'<meta name="twitter:description" content="{desc_esc}">')
        elif stripped.startswith('<link rel="canonical" href="'):
            out_lines.append(f'<link rel="canonical" href="{canonical_url}">')
        elif stripped.startswith('"headline":'):
            out_lines.append(f'  "headline": {json.dumps(title)},')
        elif stripped.startswith('"description":'):
            out_lines.append(f'  "description": {json.dumps(summary)},')
        elif stripped.startswith('"datePublished":'):
            out_lines.append(f'  "datePublished": "{date_str}",')
        elif stripped.startswith('"dateModified":'):
            out_lines.append(f'  "dateModified": "{date_str}",')
        elif stripped.startswith('"url": "https://worldpulse.fyi/news/'):
            trailing = "," if stripped.endswith(",") else ""
            out_lines.append(f'  "url": "{canonical_url}"{trailing}')
        elif stripped.startswith('"mainEntityOfPage":'):
            out_lines.append(f'  "mainEntityOfPage": "{canonical_url}"')
        elif stripped.startswith('<span class="tag">'):
            out_lines.append(f'  <span class="tag">{html.escape(tag)}</span>')
        elif stripped.startswith("<h1>"):
            out_lines.append(f"  <h1>{title_esc}</h1>")
        elif stripped.startswith('<p class="updated">'):
            out_lines.append(f'  <p class="updated">Published {date_label} &middot; Sourced from {html.escape(source_name)}</p>')
            skip_until_main_close = True
            out_lines.append("")
            out_lines.extend(new_body)
        elif stripped.startswith("<main"):
            in_head_section = False
            out_lines.append(line)
        else:
            out_lines.append(line)

    return "\n".join(out_lines)


def main():
    manifest = load_manifest()
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    published_this_run = 0
    new_entries = []

    for feed in FEEDS:
        if published_this_run >= MAX_NEW_ITEMS_PER_RUN:
            break
        try:
            raw = fetch(feed["url"])
            items = parse_rss(raw) if feed["kind"] == "rss" else parse_atom(raw)
        except Exception as e:
            print(f"WARN: failed to fetch {feed['name']}: {e}", file=sys.stderr)
            continue

        for item in items:
            if published_this_run >= MAX_NEW_ITEMS_PER_RUN:
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
                extra_paragraphs = usgs_body_paragraphs(item["title"])
            else:
                if not item["description"]:
                    continue
                summary = truncate(item["description"], MAX_SUMMARY_CHARS)
                extra_paragraphs = reliefweb_body_paragraphs(item["title"], summary)
            slug = f"{today}-{slugify(item['title'])}"
            if any(e.get("slug") == slug for e in manifest) or any(e.get("slug") == slug for e in new_entries):
                continue

            article_html = build_article_html(
                template=template,
                title=item["title"],
                tag=feed["tag"],
                date_str=today,
                summary=summary,
                source_name=feed["name"],
                source_url=item["link"],
                canonical_slug=slug,
                extra_paragraphs=extra_paragraphs,
            )
            with open(f"{NEWS_DIR}/{slug}.html", "w", encoding="utf-8") as f:
                f.write(article_html)

            entry = {
                "slug": slug,
                "title": item["title"],
                "date": today,
                "summary": summary,
                "url": f"/news/{slug}.html",
                "sources": [{"name": feed["name"], "url": item["link"]}],
            }
            new_entries.append(entry)
            published_this_run += 1
            print(f"Published: {item['title']}")

    if not new_entries:
        print("No new items to publish this run.")
        return

    manifest = new_entries + manifest
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(SITEMAP_PATH, encoding="utf-8") as f:
        sitemap = f.read()
    inserts = "".join(
        f"  <url>\n    <loc>https://worldpulse.fyi{e['url']}</loc>\n"
        f"    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>\n"
        for e in new_entries
    )
    sitemap = sitemap.replace("</urlset>", inserts + "</urlset>")
    with open(SITEMAP_PATH, "w", encoding="utf-8") as f:
        f.write(sitemap)

    print(f"Done. Published {len(new_entries)} new item(s).")


if __name__ == "__main__":
    main()
