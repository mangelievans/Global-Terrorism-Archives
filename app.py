from flask import Flask, jsonify, render_template, request

from news_service import search_news


app = Flask(__name__)


def normalize_query(value):
    if value is None:
        return ""
    return str(value).strip()[:100]


@app.get("/")
def home():
    query = normalize_query(request.args.get("q", ""))
    stories, status_message = search_news(query)
    return render_template(
        "index.html",
        query=query,
        stories=stories,
        status_message=status_message,
    )


@app.get("/api/stories")
def live_stories():
    query = normalize_query(request.args.get("q", ""))
    stories, status_message = search_news(query)
    response = jsonify(
        query=query,
        stories=stories,
        status_message=status_message,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
