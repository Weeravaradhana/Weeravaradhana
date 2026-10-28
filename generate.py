import os
import json
import urllib.request
from collections import Counter
from pathlib import Path
from html import escape

USER = os.getenv('PROFILE_USERNAME', 'Weeravaradhana')
TOKEN = os.getenv('GH_TOKEN', '')
OUT = Path('assets')
OUT.mkdir(exist_ok=True)


def get(path):
    req = urllib.request.Request('https://api.github.com' + path, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'github-profile-svg-generator',
        **({'Authorization': 'Bearer ' + TOKEN} if TOKEN else {})
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def repositories():
    result = []
    page = 1
    while True:
        batch = get(f'/users/{USER}/repos?type=owner&per_page=100&page={page}')
        result.extend(batch)
        if len(batch) < 100:
            return result
        page += 1


def base(title, body, height=210):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="470" height="{height}" viewBox="0 0 470 {height}" role="img" aria-label="{escape(title)}">
<rect x="1" y="1" width="468" height="{height-2}" rx="15" fill="#0d111f" stroke="#263657"/>
<text x="25" y="39" font-size="20" font-family="Arial,sans-serif" font-weight="bold" fill="#70a5fd">{escape(title)}</text>
{body}
</svg>'''


def write(name, svg):
    (OUT / name).write_text(svg, encoding='utf-8')


def main():
    repos = [r for r in repositories() if not r['fork']]
    stars = sum(r['stargazers_count'] for r in repos)
    forks = sum(r['forks_count'] for r in repos)
    user = get('/users/' + USER)
    values = [('Public Repos', len(repos)), ('Total Stars', stars), ('Total Forks', forks), ('Followers', user['followers'])]
    rows = ''.join(f'<text x="28" y="{79+i*34}" font-size="15" fill="#a9b1d6" font-family="Arial,sans-serif">{escape(label)}</text><text x="437" y="{79+i*34}" text-anchor="end" font-size="17" font-weight="bold" fill="#7dcfff" font-family="Arial,sans-serif">{value:,}</text>' for i,(label,value) in enumerate(values))
    write('github-stats.svg', base('GitHub Public Stats', rows))

    counts = Counter()
    for repo in repos:
        languages = get(f"/repos/{USER}/{repo['name']}/languages")
        counts.update(languages)
    total = sum(counts.values())
    colors = ['#7aa2f7','#bb9af7','#9ece6a','#e0af68','#f7768e','#73daca','#7dcfff','#c0caf5']
    top = counts.most_common(6)
    if not top:
        content = '<text x="28" y="90" fill="#a9b1d6" font-size="15">No public repository language data yet.</text>'
    else:
        content = ''
        for i,(lang,amount) in enumerate(top):
            y = 72+i*37
            percent = amount/total*100
            color = colors[i%len(colors)]
            content += f'<circle cx="33" cy="{y-5}" r="6" fill="{color}"/><text x="49" y="{y}" font-size="14" fill="#c0caf5" font-family="Arial,sans-serif">{escape(lang)}</text><text x="438" y="{y}" text-anchor="end" font-size="14" fill="#c0caf5" font-family="Arial,sans-serif">{percent:.1f}%</text>'
            content += f'<rect x="28" y="{y+7}" width="410" height="5" rx="2" fill="#22283e"/><rect x="28" y="{y+7}" width="{410*amount/total:.2f}" height="5" rx="2" fill="{color}"/>'
    write('top-languages.svg', base('Most Used Languages', content, 315))
    print(f'Generated SVGs for {USER}: {len(repos)} source repositories, {len(counts)} languages')


if __name__ == '__main__':
    main()
