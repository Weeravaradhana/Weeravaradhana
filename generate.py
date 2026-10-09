import json, os, urllib.request, html, datetime
from pathlib import Path

ROOT = Path(__file__).parent
ASSETS = ROOT / 'assets'
ASSETS.mkdir(exist_ok=True)
USER = 'Weeravaradhana'
HEADERS = {'Accept': 'application/vnd.github+json', 'User-Agent': 'profile-readme-generator'}
if os.getenv('GH_TOKEN'):
    HEADERS['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']

def get(endpoint):
    try:
        req = urllib.request.Request('https://api.github.com' + endpoint, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.load(r)
    except Exception as exc:
        print('GitHub API unavailable:', exc)
        return []

def svg(texts, filename, title, link=False):
    lines = []
    for i, t in enumerate(texts[:7]):
        safe = html.escape(str(t)[:94])
        y = 100 + i * 47
        lines.append(f'<text x="32" y="{y}" fill="#d6edff" font-size="17" font-family="monospace" opacity="0"><animate attributeName="opacity" values="0;1;1;0" dur="9s" begin="{i*0.5}s" repeatCount="indefinite"/><tspan fill="#2bd7ba">❯ </tspan>{safe}</text>')
    height = max(210, 130 + len(lines)*47)
    content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}"><rect width="900" height="{height}" rx="18" fill="#0b1220"/><rect x="1" y="1" width="898" height="{height-2}" rx="18" fill="none" stroke="#1d4863"/><circle cx="26" cy="28" r="6" fill="#ff605c"/><circle cx="48" cy="28" r="6" fill="#ffbd44"/><circle cx="70" cy="28" r="6" fill="#00ca4e"/><text x="100" y="34" fill="#62c9eb" font-family="monospace" font-size="17">{html.escape(title)}</text><path d="M20 51H880" stroke="#1d4863"/> {''.join(lines)}<rect x="30" y="{height-35}" width="9" height="18" fill="#2bd7ba"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect></svg>'''
    (ASSETS / filename).write_text(content, encoding='utf-8')

tech = ['Java • Spring Boot • Spring Security • JPA', 'Node.js • NestJS • TypeScript • Next.js', 'Docker • GitHub Actions • Linux • AWS', 'Kafka • Redis • PostgreSQL • MongoDB', 'REST APIs • Microservices • CI/CD • Monitoring']
svg(tech, 'tech-marquee.svg', 'stack --watch')
repos = get(f'/users/{USER}/repos?per_page=100&sort=updated')
repos = [r for r in repos if not r.get('fork') and r.get('name','').lower() != USER.lower()]
repos.sort(key=lambda r: (r.get('stargazers_count',0), r.get('pushed_at','')), reverse=True)
projects = [f"{r['name']}  /  {r.get('language') or 'multi-language'}  /  ★ {r.get('stargazers_count',0)}" for r in repos[:6]]
svg(projects or ['Projects refresh when GitHub Actions runs'], 'projects.svg', 'projects --live')
events = get(f'/users/{USER}/events/public?per_page=15')
items = []
for event in events[:6]:
    stamp = (event.get('created_at') or '')[:10]
    name = event.get('repo', {}).get('name','').split('/')[-1]
    items.append(f"{stamp}  {event.get('type','Activity').replace('Event','')}  {name}")
svg(items or ['Public events will appear after the next refresh'], 'activity.svg', 'git log --public')
print('Generated dynamic SVG panels:', datetime.datetime.now(datetime.timezone.utc).isoformat())
