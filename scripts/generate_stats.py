
import os
import json
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict
from xml.sax.saxutils import escape

# ==========================================
# CONFIGURATION
# ==========================================

USERNAME = "sirushtika4"
TOKEN = os.environ["GITHUB_TOKEN"]
API_URL = "https://api.github.com/graphql"

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ASSETS.mkdir(exist_ok=True)

BG = "#0D1117"
CARD = "#161B22"
ACCENT = "#22D3EE"
TEXT = "#C9D1D9"
BORDER = "#30363D"

NOW = datetime.now(timezone.utc)
UPDATED = NOW.strftime("%Y-%m-%d %H:%M UTC")

# ==========================================
# GITHUB GRAPHQL API
# ==========================================

QUERY = """
query($username: String!, $cursor: String) {
  user(login: $username) {
    login
    followers {
      totalCount
    }
    pullRequests {
      totalCount
    }
    issues {
      totalCount
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
    repositories(
      first: 50
      after: $cursor
      ownerAffiliations: OWNER
      privacy: PUBLIC
      isFork: false
    ) {
      totalCount
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        name
        stargazerCount
        languages(first: 100) {
          edges {
            size
            node {
              name
              color
            }
          }
        }
      }
    }
  }
}
"""


def fetch_page(cursor=None):
    payload = json.dumps({
        "query": QUERY,
        "variables": {
            "username": USERNAME,
            "cursor": cursor
        }
    }).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "Profile-Analytics"
        }
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.load(response)

    if result.get("errors"):
        raise RuntimeError(result["errors"])

    if not result.get("data", {}).get("user"):
        raise RuntimeError("GitHub user was not found.")

    return result["data"]["user"]


def fetch_github_data():
    user = fetch_page()
    connection = user["repositories"]
    repositories = list(connection["nodes"])

    while connection["pageInfo"]["hasNextPage"]:
        cursor = connection["pageInfo"]["endCursor"]
        page = fetch_page(cursor)
        connection = page["repositories"]
        repositories.extend(connection["nodes"])

    return user, repositories


# ==========================================
# SVG HELPER FUNCTIONS
# ==========================================

def svg_start(width, height, title):
    return f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}" height="{height}"
     viewBox="0 0 {width} {height}"
     role="img">
  <title>{escape(title)}</title>
  <rect x="1" y="1"
        width="{width - 2}"
        height="{height - 2}"
        rx="12"
        fill="{BG}"
        stroke="{BORDER}"/>
  <g font-family="Segoe UI, Arial, sans-serif">
"""


def svg_text(x, y, value, size=16,
             color=TEXT, weight="normal",
             anchor="start"):

    return (
        f'<text x="{x}" y="{y}" '
        f'font-size="{size}" '
        f'fill="{color}" '
        f'font-weight="{weight}" '
        f'text-anchor="{anchor}">'
        f'{escape(str(value))}</text>'
    )


def save_svg(filename, content):
    content += "</g></svg>"

    output = ASSETS / filename
    output.write_text(content, encoding="utf-8")

    print(f"Generated: {output.name}")


# ==========================================
# GITHUB STATISTICS CARD
# ==========================================

def generate_stats(user, repositories):

    total_stars = sum(
        repo["stargazerCount"]
        for repo in repositories
    )

    contributions = user["contributionsCollection"]

    stats = [
        ("Public non-fork repositories",
         len(repositories)),
        ("Stars on those repositories",
         total_stars),
        ("Commits (last year)",
         contributions["totalCommitContributions"]),
        ("Pull requests",
         user["pullRequests"]["totalCount"]),
        ("Issues",
         user["issues"]["totalCount"]),
        ("Followers",
         user["followers"]["totalCount"])
    ]

    svg = svg_start(
        500, 330, "Sirushtika's GitHub Statistics"
    )

    svg += svg_text(
        25, 38,
        "Sirushtika's GitHub Statistics",
        21, ACCENT, "bold"
    )

    for i, (label, value) in enumerate(stats):
        y = 80 + i * 37

        svg += svg_text(25, y, label, 15)

        svg += svg_text(
            470, y, f"{value:,}",
            18, ACCENT, "bold", "end"
        )

    svg += svg_text(
        25, 310,
        f"Updated: {UPDATED}",
        11, "#8B949E"
    )

    save_svg("github-stats.svg", svg)


# ==========================================
# PROGRAMMING LANGUAGES CARD
# ==========================================

def generate_languages(repositories):

    language_sizes = defaultdict(int)
    colors = {}

    for repo in repositories:

        if repo["name"] == USERNAME:
            continue

        for edge in repo["languages"]["edges"]:

            language = edge["node"]["name"]
            size = edge["size"]

            language_sizes[language] += size
            colors[language] = (
                edge["node"]["color"] or ACCENT
            )

    total = sum(language_sizes.values())

    languages = sorted(
        language_sizes.items(),
        key=lambda item: item[1],
        reverse=True
    )

    top_languages = languages[:6]

    svg = svg_start(
        500, 330, "Programming Languages"
    )

    svg += svg_text(
        25, 38,
        "Most Used Languages",
        22, ACCENT, "bold"
    )

    for i, (language, size) in enumerate(top_languages):

        percentage = (
            size / total * 100 if total else 0
        )

        y = 70 + i * 38

        svg += svg_text(25, y, language, 14)

        svg += svg_text(
            475, y,
            f"{percentage:.1f}%",
            14, TEXT, "normal", "end"
        )

        svg += f"""
        <rect x="25" y="{y + 8}"
              width="450" height="7"
              rx="3" fill="{BORDER}"/>
        <rect x="25" y="{y + 8}"
              width="{450 * percentage / 100:.2f}"
              height="7" rx="3"
              fill="{colors[language]}"/>
        """

    if not top_languages:
        svg += svg_text(
            25, 100,
            "No language data available."
        )

    svg += svg_text(
        25, 310,
        "Public non-fork repository language usage",
        11, "#8B949E"
    )

    save_svg("top-languages.svg", svg)


# ==========================================
# CALCULATE CONTRIBUTION STREAKS
# ==========================================

def calculate_streaks(days):

    ordered_days = sorted(
        days,
        key=lambda day: day["date"]
    )

    longest = 0
    running = 0

    for day in ordered_days:

        if day["contributionCount"] > 0:
            running += 1
            longest = max(longest, running)
        else:
            running = 0

    counts = {
        day["date"]: day["contributionCount"]
        for day in ordered_days
    }

    current = 0
    today = NOW.date()

    if counts.get(today.isoformat(), 0) == 0:
        today -= timedelta(days=1)

    while counts.get(today.isoformat(), 0) > 0:
        current += 1
        today -= timedelta(days=1)

    return current, longest


# ==========================================
# CONTRIBUTION ACTIVITY CARD
# ==========================================

def generate_contributions(user):

    calendar = user[
        "contributionsCollection"
    ]["contributionCalendar"]

    weeks = calendar["weeks"]

    days = [
        day
        for week in weeks
        for day in week["contributionDays"]
    ]

    current, longest = calculate_streaks(days)

    svg = svg_start(
        1000, 300, "Contribution Activity"
    )

    svg += svg_text(
        30, 38,
        "Contribution Activity",
        24, ACCENT, "bold"
    )

    summary = [
        ("Annual Contributions",
         calendar["totalContributions"]),
        ("Current Streak", current),
        ("Longest Streak", longest)
    ]

    for i, (label, value) in enumerate(summary):

        x = 170 + i * 330

        svg += svg_text(
            x, 80, value,
            30, ACCENT, "bold", "middle"
        )

        svg += svg_text(
            x, 105, label,
            15, TEXT, "normal", "middle"
        )

    palette = [
        "#161B22",
        "#164E63",
        "#0E7490",
        "#0891B2",
        "#22D3EE"
    ]

    for x, week in enumerate(weeks):

        for day in week["contributionDays"]:

            count = day["contributionCount"]
            weekday = date.fromisoformat(
                day["date"]
            ).weekday()

            y = (weekday + 1) % 7

            if count == 0:
                level = 0
            elif count <= 2:
                level = 1
            elif count <= 5:
                level = 2
            elif count <= 9:
                level = 3
            else:
                level = 4

            svg += f"""
            <rect x="{25 + x * 17}"
                  y="{135 + y * 17}"
                  width="13" height="13"
                  rx="2"
                  fill="{palette[level]}">
              <title>{day["date"]}: {count} contributions</title>
            </rect>
            """

    svg += svg_text(
        30, 285,
        f"Last updated: {UPDATED}",
        12, "#8B949E"
    )

    save_svg("contributions.svg", svg)


# ==========================================
# MAIN PROGRAM
# ==========================================

def main():

    print("Fetching GitHub analytics...")

    user, repositories = fetch_github_data()

    generate_stats(user, repositories)
    generate_languages(repositories)
    generate_contributions(user)

    print("Analytics generated successfully!")


if __name__ == "__main__":
    main()
