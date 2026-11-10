(() => {
    const results = document.querySelector(".results[data-refresh-url]");
    if (!results) return;

    const refreshUrl = results.dataset.refreshUrl;
    const query = document.querySelector("#query")?.value ?? "";
    let list = document.querySelector("#story-list");
    const status = document.querySelector("#source-status");
    const count = document.querySelector("#result-count");
    const refreshInterval = 60_000;
    let refreshing = false;

    function createElement(tag, className, text) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    }

    function renderStory(story) {
        const card = createElement("article", "story-card");
        const meta = createElement("div", "story-meta");
        meta.append(
            createElement("span", "", story.source),
            createElement("span", "", story.published_at || "Publication date unavailable"),
        );
        card.append(meta, createElement("h3", "", story.title));

        if (story.people?.length) {
            const people = createElement("div", "people-mentioned");
            people.append(createElement("strong", "", "People mentioned in report"));
            const peopleList = createElement("ul");
            story.people.forEach((person) => peopleList.append(createElement("li", "", person)));
            people.append(
                peopleList,
                createElement(
                    "span",
                    "people-note",
                    "Names are surfaced from provider data or role-labeled headlines; review the linked report for context.",
                ),
            );
            card.append(people);
        }

        if (story.language) {
            card.append(createElement("p", "story-source", `Language: ${story.language}`));
        }

        if (/^https?:\/\//i.test(story.url)) {
            const link = createElement("a");
            link.href = story.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";
            const indicator = createElement("span", "", "↗");
            indicator.setAttribute("aria-hidden", "true");
            link.append(document.createTextNode("View source report "), indicator);
            card.append(link);
        }
        return card;
    }

    function updateStories(stories) {
        const replacement = stories.length
            ? createElement("div", "story-list")
            : createElement("div", "empty-state");

        if (stories.length) {
            stories.forEach((story) => replacement.append(renderStory(story)));
        } else {
            replacement.append(
                createElement("h3", "", "No matching stories"),
                createElement(
                    "p",
                    "",
                    "Try another keyword. If no matching articles are available from the news source, results may be empty.",
                ),
            );
        }

        replacement.id = "story-list";
        list.replaceWith(replacement);
        list = replacement;
        count.textContent = String(stories.length);
    }

    async function refreshStories() {
        if (refreshing || document.hidden) return;
        refreshing = true;

        try {
            const url = new URL(refreshUrl, window.location.origin);
            if (query) url.searchParams.set("q", query);
            const response = await fetch(url, { cache: "no-store" });
            if (!response.ok) throw new Error(`Refresh failed with HTTP ${response.status}`);

            const data = await response.json();
            updateStories(data.stories);
            status.textContent = `${data.status_message} Last checked ${new Date().toLocaleTimeString()}.`;
        } catch (error) {
            console.error("Could not refresh live news results.", error);
            status.textContent = "Live refresh failed. Showing the most recent results; will retry shortly.";
        } finally {
            refreshing = false;
        }
    }

    window.setInterval(refreshStories, refreshInterval);
})();
