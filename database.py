"""SQLite storage for article metadata returned by the news provider."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parent / "instance" / "stories.sqlite3"


@contextmanager
def connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database():
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stories (
                url TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                published_at TEXT,
                language TEXT,
                topic TEXT NOT NULL DEFAULT 'unclassified',
                people TEXT NOT NULL DEFAULT '[]',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(stories)")
        }
        if "topic" not in columns:
            connection.execute(
                "ALTER TABLE stories ADD COLUMN topic TEXT NOT NULL DEFAULT 'unclassified'"
            )
        if "people" not in columns:
            connection.execute(
                "ALTER TABLE stories ADD COLUMN people TEXT NOT NULL DEFAULT '[]'"
            )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_stories_published_at ON stories(published_at)"
        )


def save_stories(stories):
    if not stories:
        return

    with connect() as connection:
        connection.executemany(
            """
            INSERT INTO stories (url, title, source, published_at, language, topic, people, first_seen_at, last_seen_at)
            VALUES (:url, :title, :source, :published_at, :language, :topic, :people, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                source = excluded.source,
                published_at = excluded.published_at,
                language = excluded.language,
                topic = excluded.topic,
                people = excluded.people,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            [
                {
                    **story,
                    "topic": story.get("topic", "global_terrorism"),
                    "people": json.dumps(story.get("people", []), ensure_ascii=False),
                }
                for story in stories
            ],
        )


def find_cached_stories(query, limit=50):
    normalized_query = str(query or "").strip()
    terms = [term for term in normalized_query.casefold().split() if term]
    conditions = []
    parameters = []
    for term in terms:
        conditions.append(
            "(lower(title) LIKE ? OR lower(source) LIKE ? OR lower(url) LIKE ? OR lower(people) LIKE ?)"
        )
        wildcard = f"%{term}%"
        parameters.extend((wildcard, wildcard, wildcard, wildcard))

    where = " AND ".join(conditions) if conditions else "1 = 1"
    where += " AND topic = ?"
    parameters.extend(("global_terrorism", limit))
    with connect() as connection:
        rows = connection.execute(
            f"SELECT title, source, url, published_at, language, people FROM stories WHERE {where} "
            "ORDER BY published_at DESC LIMIT ?",
            parameters,
        ).fetchall()
    stories = []
    for row in rows:
        story = dict(row)
        try:
            story["people"] = json.loads(story["people"])
        except json.JSONDecodeError:
            story["people"] = []
        stories.append(story)
    return stories
