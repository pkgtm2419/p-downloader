"""
Automated RSS / Atom Torrent Feed Watcher for P-Downloader.
Polls torrent tracker feeds, applies regex filters to releases,
and enqueues matching items into DownloadEngine.
"""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import requests


@dataclass
class TorrentRSSItem:
    title: str
    link: str
    guid: str
    published: str = ""


@dataclass
class TorrentRSSFeed:
    feed_id: str
    name: str
    url: str
    filter_pattern: str
    category: str = "Torrents"
    auto_download: bool = True
    last_guid: str = ""


def parse_rss_feed(xml_text: str) -> List[TorrentRSSItem]:
    """
    Parses RSS 2.0 or Atom XML content into a list of TorrentRSSItem objects.
    """
    items: List[TorrentRSSItem] = []
    if not xml_text or not xml_text.strip():
        return items

    try:
        root = ET.fromstring(xml_text)
    except Exception as e:
        raise ValueError(f"Invalid RSS/Atom XML feed: {e}")

    # Check RSS 2.0 (<rss><channel><item>)
    channel = root.find("channel")
    if channel is not None:
        for item_node in channel.findall("item"):
            title = (item_node.findtext("title") or "").strip()
            link = (item_node.findtext("link") or "").strip()

            # Enclosure support
            enclosure = item_node.find("enclosure")
            if enclosure is not None and enclosure.get("url"):
                link = enclosure.get("url")

            guid = (item_node.findtext("guid") or link or title).strip()
            pub_date = (item_node.findtext("pubDate") or "").strip()

            if title and link:
                items.append(TorrentRSSItem(
                    title=title,
                    link=link,
                    guid=guid,
                    published=pub_date
                ))
        return items

    # Check Atom (<feed><entry>)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns) or root.findall("entry"):
        title = (entry.findtext("atom:title", namespaces=ns) or entry.findtext("title") or "").strip()
        link_elem = entry.find("atom:link", ns) or entry.find("link")
        link = link_elem.get("href", "").strip() if link_elem is not None else ""
        guid = (entry.findtext("atom:id", namespaces=ns) or entry.findtext("id") or link).strip()
        pub = (entry.findtext("atom:updated", namespaces=ns) or entry.findtext("updated") or "").strip()

        if title and link:
            items.append(TorrentRSSItem(
                title=title,
                link=link,
                guid=guid,
                published=pub
            ))

    return items


def filter_rss_items(items: List[TorrentRSSItem], pattern: str) -> List[TorrentRSSItem]:
    """
    Filters RSS items whose titles match a user regular expression.
    """
    if not pattern:
        return items

    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        raise ValueError(f"Invalid regex filter pattern '{pattern}': {e}")

    matched = []
    for item in items:
        if compiled.search(item.title):
            matched.append(item)
    return matched


class TorrentRSSWatcher:
    """
    Monitors RSS feeds and enqueues newly discovered matching items.
    """
    def __init__(self, timeout_sec: int = 15):
        self.timeout_sec = timeout_sec
        self.seen_guids = set()

    def fetch_feed(self, feed_url: str) -> List[TorrentRSSItem]:
        headers = {"User-Agent": "P-Downloader-RSS/1.1.0"}
        resp = requests.get(feed_url, headers=headers, timeout=self.timeout_sec)
        resp.raise_for_status()
        return parse_rss_feed(resp.text)

    def check_feed(self, feed: TorrentRSSFeed) -> List[TorrentRSSItem]:
        """
        Fetches feed, filters by pattern, and yields only new items not yet seen.
        """
        raw_items = self.fetch_feed(feed.url)
        matched = filter_rss_items(raw_items, feed.filter_pattern)

        new_items = []
        for item in matched:
            if item.guid not in self.seen_guids:
                new_items.append(item)
                self.seen_guids.add(item.guid)

        if new_items:
            feed.last_guid = new_items[0].guid
        return new_items
