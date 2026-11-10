# Global terrorism archive

Global terrorism archive is a searchable collection of sourced reporting metadata about terrorism and counter-terrorism. It searches GDELT's global news index first and uses Google News RSS as a fallback. Both searches remain terrorism-focused; the system does not return general keyword results as a fallback.

The archive stores headlines, publisher names, source links, dates, language, and people explicitly identified by provider metadata or leadership/official titles in headlines when available. Names are linked to the source report and are not independently verified identities or claims about a person's role. It links readers to publishers rather than copying full article text. Search results reflect the sources' available coverage and are not an exhaustive or independently verified record of every event.

The page fetches fresh provider results when opened or searched and checks for updates every 60 seconds while it remains open. Update timing and coverage depend on GDELT and Google News; this is periodic polling, not a guarantee of instantaneous publication.

## Run locally

1. Open PowerShell in this project folder.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Start the application:

   ```powershell
   python app.py
   ```

5. Open `http://127.0.0.1:5000`.

The SQLite archive is created at `instance/stories.sqlite3` when first used. Each successful live search stores or updates its source records. Previously saved records that predate topic classification are marked unclassified and excluded from archive search results.

## Search and sources

- GDELT searches its `TERROR` theme with a rolling three-month window, returning up to 50 records.
- If GDELT has no results or is unavailable, Google News RSS is queried with the entered terms and a terrorism term. The feed is not constrained to a single country.
- Cached entries are shown only when they were stored as part of a terrorism-focused search.
- The default search shows recent global terrorism reporting.

News coverage, languages, and publication dates vary by provider. A source link is provided for readers to review the original reporting; inclusion in the archive does not establish that an allegation or event has been independently confirmed.

GDELT documentation: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

## Project structure

```text
terrorism/
├── app.py                 # Flask application and search route
├── database.py            # SQLite schema, storage, and archive search
├── news_service.py        # Global terrorism news retrieval
├── requirements.txt       # Python dependencies
├── templates/
│   ├── base.html          # Shared application layout
│   └── index.html         # Search and results page
├── static/
│   └── css/
│       └── style.css      # Application styles
└── tests/
    └── test_news_service.py
```
