
import os
import json
import urllib.request
import urllib.error
import datetime
import html
import pathlib

USER = os.getenv("GITHUB_USERNAME", "Weeravaradhana")
TOKEN = os.getenv("GH_STATS_TOKEN") or os.getenv("GITHUB_TOKEN")

if not TOKEN:
    raise SystemExit("Missing GitHub API token")

OUT = pathlib.Path("assets")
OUT.mkdir(exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "User-Agent": "github-profile-dashboard",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


def request(url, data=None):
    headers = dict(HEADERS)

    if data is not None:
        headers["Content-Type"] = "application/json"

    payload = (
        json.dumps(data).encode()
        if data is not None else None
    )

    req = urllib.request.Request(
        url,
        data=payload,
        headers=headers
    )

    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)


def graphql(query, variables):
    result = request(
        "https://api.github.com/graphql",
        {
            "query": query,
            "variables": variables
        }
    )

    if result.get("errors"):
        raise RuntimeError(str(result["errors"]))

    return result["data"]


now = datetime.datetime.now(datetime.timezone.utc)
start = now - datetime.timedelta(days=365)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    name
    login

    followers {
      totalCount
    }

    repositories(
      privacy: PUBLIC
      ownerAffiliations: OWNER
    ) {
      totalCount
    }

    contributionsCollection(
      from: $from
      to: $to
    ) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount

      contributionCalendar {
        totalContributions
      }
    }
  }
}
"""

user = graphql(
    query,
    {
        "login": USER,
        "from": start.isoformat(),
        "to": now.isoformat()
    }
)["user"]

if not user:
    raise SystemExit("GitHub user not found")

contributions = user["contributionsCollection"]

# Retrieve all public repositories

repositories = []
page = 1

while True:
    batch = request(
        f"https://api.github.com/users/{USER}/repos"
        f"?per_page=100&page={page}&type=owner"
    )

    if not isinstance(batch, list):
        raise RuntimeError("Invalid repository response")

    repositories.extend(
        repo for repo in batch
        if not repo["fork"]
        and not repo.get("private", False)
    )

    if len(batch) < 100:
        break

    page += 1

    if page > 50:
        raise RuntimeError("Pagination safety limit reached")


total_stars = sum(
    repo["stargazers_count"]
    for repo in repositories
)

total_forks = sum(
    repo["forks_count"]
    for repo in repositories
)

# Calculate programming languages

languages = {}

for repo in repositories:
    try:
        data = request(repo["languages_url"])

        for language, byte_count in data.items():
            languages[language] = (
                languages.get(language, 0) + byte_count
            )

    except urllib.error.HTTPError as error:
        if error.code in (403, 429):
            raise
        print(f"Language API error: {error}")


# SVG design configuration

BG = "#0d111c"
FG = "#dce8fa"
MUTED = "#91a3c2"
CYAN = "#23c7e8"
BORDER = "#28436a"


def escape(value):
    return html.escape(str(value), quote=True)


def text(x, y, value, size=17, color=FG, weight=500):
    return (
        f'<text x="{x}" y="{y}" '
        f'fill="{color}" font-size="{size}" '
        f'font-family="Arial,Helvetica,sans-serif" '
        f'font-weight="{weight}">'
        f'{escape(value)}</text>'
    )


def svg(width, height, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<rect x="1" y="1" '
        f'width="{width-2}" height="{height-2}" '
        f'rx="16" fill="{BG}" stroke="{BORDER}"/>'
        f'{body}</svg>'
    )


def save_svg(filename, content):
    path = OUT / filename
    path.write_text(content, encoding="utf-8")
    print(f"Generated: {path}")


# GitHub statistics
# Contribution counts are for the last 365 days.

metrics = [
    (
        "Commits (365d)",
        contributions["totalCommitContributions"]
    ),
    (
        "Pull Requests (365d)",
        contributions["totalPullRequestContributions"]
    ),
    (
        "Issues (365d)",
        contributions["totalIssueContributions"]
    ),
    (
        "PR Reviews (365d)",
        contributions["totalPullRequestReviewContributions"]
    ),
    (
        "Contributions (365d)",
        contributions["contributionCalendar"]["totalContributions"]
    ),
    (
        "Public Repos",
        user["repositories"]["totalCount"]
    ),
    (
        "Stars",
        total_stars
    ),
    (
        "Forks",
        total_forks
    ),
    (
        "Followers",
        user["followers"]["totalCount"]
    )
]

width = 780
height = 385

body = text(
    28, 43,
    f"{USER} | Developer Metrics",
    24, CYAN, 700
)

body += text(
    28, 67,
    f"Activity: {start.date()} to {now.date()}",
    12, MUTED
)

for index, (label, value) in enumerate(metrics):
    row, col = divmod(index, 3)

    x = 28 + col * 250
    y = 108 + row * 87

    body += (
        f'<rect x="{x}" y="{y}" '
        f'width="228" height="72" rx="10" '
        f'fill="#142239"/>'
    )

    body += text(
        x + 14, y + 25,
        label, 13, MUTED
    )

    body += text(
        x + 14, y + 57,
        f"{value:,}", 27, FG, 700
    )

body += text(
    28, 371,
    "GitHub API | Automatically updated daily",
    11, MUTED
)

save_svg(
    "github-stats.svg",
    svg(width, height, body)
)


# Top programming languages

items = sorted(
    languages.items(),
    key=lambda item: item[1],
    reverse=True
)[:8]

total_bytes = sum(languages.values())

colors = [
    "#23c7e8",
    "#7aa2f7",
    "#bb9af7",
    "#9ece6a",
    "#e0af68",
    "#f7768e",
    "#73daca",
    "#c0caf5"
]

body = text(
    28, 43,
    "Top Programming Languages",
    24, CYAN, 700
)

body += text(
    28, 67,
    "Public non-fork repositories",
    12, MUTED
)

if not items:
    body += text(
        28, 115,
        "No public language data available",
        16, MUTED
    )

for index, (language, byte_count) in enumerate(items):
    y = 105 + index * 42

    percentage = (
        100 * byte_count / total_bytes
        if total_bytes else 0
    )

    body += text(
        28, y,
        language, 14, FG, 600
    )

    body += text(
        683, y,
        f"{percentage:.1f}%",
        14, MUTED
    )

    body += (
        f'<rect x="28" y="{y+8}" '
        f'width="690" height="11" '
        f'rx="5" fill="#1c2a41"/>'
    )

    body += (
        f'<rect x="28" y="{y+8}" '
        f'width="{690*percentage/100:.2f}" '
        f'height="11" rx="5" '
        f'fill="{colors[index]}"/>'
    )

body += text(
    28, 480,
    "Language percentages are calculated using code bytes.",
    11, MUTED
)

save_svg(
    "top-languages.svg",
    svg(780, 500, body)
)

print("GitHub profile dashboard generated successfully!")
