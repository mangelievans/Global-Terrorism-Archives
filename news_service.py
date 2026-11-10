"""Fetch current article metadata from GDELT and persist it in SQLite."""

import json
import re
from xml.etree import ElementTree
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from database import find_cached_stories, initialize_database, save_stories


GDELT_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_NEWS_ENDPOINT = "https://news.google.com/rss/search"
MAX_RESULTS = 50
ARCHIVE_TOPIC = "global_terrorism"
ROLE_NAME_PATTERN = re.compile(
    r"(?i:\b(?:president|prime minister|minister|foreign minister|interior minister|"
    r"defense minister|secretary(?:-general)?|leader|commander|chief|head|"
    r"founder|spokesperson|general|king|queen|emir|ayatollah))"
    r"(?:\s+of\s+[A-Z][\w'’-]+)?\s+"
    r"(?P<name>[A-Z][\w'’-]+(?:\s+(?:(?:bin|ibn|al|el|de|van|von)\s+)?[A-Z][\w'’-]+){1,3})"
)


def normalize_query(value):
    if value is None:
        return ""
    return str(value).strip()[:100]


def extract_people(article, title):
    provided_people = article.get("people", article.get("persons", article.get("person", [])))
    if isinstance(provided_people, str):
        provided_people = re.split(r"[,;]", provided_people)
    if not isinstance(provided_people, (list, tuple, set)):
        provided_people = []

    people = []
    seen = set()
    for candidate in [*provided_people, *(match.group("name") for match in ROLE_NAME_PATTERN.finditer(title))]:
        if not isinstance(candidate, str):
            continue
        name = " ".join(candidate.split()).strip(" ,.;:")
        normalized_name = name.casefold()
        if name and normalized_name not in seen and len(name) <= 100:
            people.append(name)
            seen.add(normalized_name)
        if len(people) == 5:
            break
    return people


def fetch_from_gdelt(query):
    normalized_query = normalize_query(query)
    # GDELT's TERROR theme keeps results focused on terrorism-related reporting.
    search_query = f"theme:TERROR {normalized_query}".strip()
    parameters = urlencode(
        {
            "query": search_query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": MAX_RESULTS,
            "sort": "datedesc",
            "timespan": "3months",
        }
    )
    request = Request(
        f"{GDELT_ENDPOINT}?{parameters}",
        headers={"User-Agent": "GlobalTerrorismArchive/1.0"},
    )

    with urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, dict):
        return []

    articles = payload.get("articles")
    if not isinstance(articles, list):
        return []

    records = []
    for article in articles:
        if not isinstance(article, dict):
            continue

        article_url = (article.get("url") or "").strip()
        title = (article.get("title") or "").strip()
        if not article_url or not title:
            continue

        domain = (article.get("domain") or urlparse(article_url).netloc).strip()
        records.append(
            {
                "url": article_url,
                "title": title,
                "source": domain,
                "published_at": article.get("seendate") or None,
                "language": article.get("language") or None,
                "topic": ARCHIVE_TOPIC,
                "people": extract_people(article, title),
            }
        )
    return records


def fetch_from_google_news(query):
    normalized_query = normalize_query(query)
    search_query = normalized_query
    if "terror" not in normalized_query.casefold():
        search_query = f"{search_query} terrorism".strip()

    parameters = urlencode(
        {
            "q": search_query or "terrorism",
        }
    )
    request = Request(
        f"{GOOGLE_NEWS_ENDPOINT}?{parameters}",
        headers={"User-Agent": "GlobalTerrorismArchive/1.0"},
    )

    with urlopen(request, timeout=15) as response:
        payload = response.read()

    root = ElementTree.fromstring(payload)
    records = []
    for article in root.findall("./channel/item")[:MAX_RESULTS]:
        article_url = (article.findtext("link") or "").strip()
        title = (article.findtext("title") or "").strip()
        if not article_url or not title:
            continue

        source_element = article.find("source")
        source = (
            (source_element.text or "").strip()
            if source_element is not None
            else urlparse(article_url).netloc
        )
        records.append(
            {
                "url": article_url,
                "title": title,
                "source": source,
                "published_at": article.findtext("pubDate") or None,
                "language": None,
                "topic": ARCHIVE_TOPIC,
                "people": extract_people({}, title),
            }
        )
    return records


def search_news(query):
    initialize_database()
    normalized_query = normalize_query(query)
    google_error = None
    try:
        stories = fetch_from_google_news(normalized_query)
    except (HTTPError, URLError, TimeoutError, ElementTree.ParseError, ValueError) as error:
        google_error = error
        stories = []

    if stories:
        save_stories(stories)
        return stories, "Live terrorism-related results from Google News are shown below."

    gdelt_error = None
    try:
        stories = fetch_from_gdelt(normalized_query)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
        gdelt_error = error
        stories = []

    if stories:
        save_stories(stories)
        return stories, "No Google News matches were available. Showing terrorism-related results from GDELT."

    cached = find_cached_stories(normalized_query)
    if cached:
        if gdelt_error or google_error:
            message = "Live news sources could not be reached. Showing matching articles saved in your database."
        else:
            message = "No live matches were found. Showing matching articles saved in your database."
        return cached, message

    if gdelt_error or google_error:
        return [], "Live news sources could not be reached, and no matching saved articles are available."
    return [], "No matching terrorism-related reports were found. Try another location, event, or organization."

