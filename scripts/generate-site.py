#!/usr/bin/env python3
"""Generates the app directory for flatpak-repo.

Writes index.html and icons/ into the repository directory (served by Pages)
and rewrites the section of README.md between the apps:start and apps:end
markers. Each line of apps.txt is "<owner>/<repo> <AppName>". The description
and release version come from GitHub; the icon comes from the app's own commit
in the repository.

Usage: generate-site.py APPS_TXT REPO_DIR BASE_URL README
Needs the gh CLI (authenticated through GH_TOKEN) and ostree.
"""
import html
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

REMOTE_NAME = "ajhub"
TITLE = "AJHub"
SUBTITLE = "AJ's Flatpak Repository"
GITHUB_MARK = (
    '<svg class="gh" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">'
    '<path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>'
    "</svg>"
)
ICON_PATHS = [
    "scalable/apps/{id}.svg",
    "512x512/apps/{id}.png",
    "256x256/apps/{id}.png",
    "128x128/apps/{id}.png",
]


def run(*args, binary=False):
    return subprocess.run(args, check=True, capture_output=True, text=not binary).stdout


def read_apps(path):
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            repo, prefix = line.split()[:2]
            yield repo, prefix


def app_ids(repo_dir):
    """Maps AppName (last component of the app ID) to (app ID, a ref)."""
    found = {}
    for ref in run("ostree", "refs", f"--repo={repo_dir}").split():
        parts = ref.split("/")
        if parts[0] == "app":
            found.setdefault(parts[1].rsplit(".", 1)[-1], (parts[1], ref))
    return found


def source_repo_url(base_url):
    """This repository's GitHub URL: GITHUB_REPOSITORY in Actions, else derived from the Pages URL."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        parsed = urlparse(base_url)
        repo = f"{parsed.hostname.split('.')[0]}/{parsed.path.strip('/')}"
    return f"https://github.com/{repo}"


def github_info(repo):
    try:
        info = json.loads(run("gh", "repo", "view", repo, "--json", "description,url"))
        release = json.loads(run("gh", "release", "view", "--repo", repo, "--json", "tagName"))
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        print(f"::warning::No GitHub information for {repo}: {error}", file=sys.stderr)
        return None
    return {
        "description": (info.get("description") or "").strip(),
        "url": info["url"],
        "version": release["tagName"],
    }


def extract_icon(repo_dir, ref, app_id, icons_dir):
    for template in ICON_PATHS:
        path = "/export/share/icons/hicolor/" + template.format(id=app_id)
        try:
            data = run("ostree", "cat", f"--repo={repo_dir}", ref, path, binary=True)
        except subprocess.CalledProcessError:
            continue
        icons_dir.mkdir(exist_ok=True)
        name = f"{app_id}{Path(path).suffix}"
        (icons_dir / name).write_bytes(data)
        return f"icons/{name}"
    return None


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}: {subtitle}</title>
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<style>
:root {{
  --bg: #fafafa; --card: #ffffff; --fg: #1e1e1e; --muted: #5e5c64;
  --border: #deddda; --accent: #1c71d8; --code: #f0f0f0;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #242424; --card: #303030; --fg: #ffffff; --muted: #c0bfbc;
    --border: #454545; --accent: #78aeed; --code: #1e1e1e;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--fg);
  font: 16px/1.5 system-ui, -apple-system, "Cantarell", "Segoe UI", sans-serif;
}}
main {{ max-width: 44rem; margin: 0 auto; padding: 2rem 1rem 4rem; }}
h1 {{ font-size: 1.75rem; margin: 0; }}
.top {{ display: flex; align-items: center; justify-content: space-between; gap: 1rem; margin-bottom: .25rem; }}
.brand {{ display: flex; align-items: center; gap: .75rem; }}
.brand img {{ flex: none; }}
.gh {{ vertical-align: -2px; margin-right: .3rem; }}
h2 {{ font-size: 1.15rem; margin: 2rem 0 .75rem; }}
p {{ margin: 0 0 1rem; color: var(--muted); }}
a {{ color: var(--accent); }}
.card {{
  background: var(--card); border: 1px solid var(--border);
  border-radius: 12px; padding: 1rem; margin-bottom: .75rem;
}}
.app {{ display: flex; gap: 1rem; align-items: flex-start; }}
.icon {{
  flex: none; width: 64px; height: 64px; border-radius: 14px;
  background: var(--code); display: grid; place-items: center;
  font-size: 1.75rem; color: var(--muted);
}}
.icon img {{ width: 64px; height: 64px; border-radius: 14px; }}
.body {{ min-width: 0; flex: 1; }}
.app h3 {{ margin: 0; font-size: 1.1rem; }}
.app h3 small {{ color: var(--muted); font-weight: normal; font-size: .85rem; margin-left: .35rem; }}
.app p {{ margin: .25rem 0 .75rem; }}
.links {{ font-size: .9rem; margin-top: .6rem; }}
.links a {{ margin-right: 1rem; }}
.cmd {{
  display: flex; align-items: flex-start; gap: .5rem; background: var(--code);
  border-radius: 8px; padding: .5rem .75rem;
}}
.cmd code {{
  flex: 1; min-width: 0; overflow-wrap: anywhere;
  font: .85rem ui-monospace, "Source Code Pro", monospace;
}}
.cmd button {{
  flex: none; font: inherit; font-size: .85rem; color: var(--accent);
  background: none; border: 1px solid var(--border); border-radius: 6px;
  padding: .15rem .6rem; cursor: pointer;
}}
</style>
</head>
<body>
<main>
<div class="top">
<div class="brand"><img src="logo.png" width="44" height="44" alt=""><h1>{title}</h1></div>
<a href="{source_url}">{mark}Source</a>
</div>
<p>{subtitle}. Apps built from source on GitHub, published as a signed Flatpak repository.</p>

<h2>Add the repository</h2>
<div class="card">
<div class="cmd"><code>flatpak remote-add --user --if-not-exists {remote} {base_url}index.flatpakrepo</code><button type="button">Copy</button></div>
</div>

<h2>Apps</h2>
{apps}
</main>
<script>
for (const button of document.querySelectorAll(".cmd button")) {{
  button.addEventListener("click", async () => {{
    const text = button.parentElement.querySelector("code").textContent;
    try {{ await navigator.clipboard.writeText(text); button.textContent = "Copied"; }}
    catch (error) {{ button.textContent = "Select and copy"; }}
    setTimeout(() => {{ button.textContent = "Copy"; }}, 2000);
  }});
}}
</script>
</body>
</html>
"""

APP = """<div class="card app">
<div class="icon">{icon}</div>
<div class="body">
<h3>{name}<small>{version}</small></h3>
<p>{description}</p>
<div class="cmd"><code>flatpak install --user {remote} {app_id}</code><button type="button">Copy</button></div>
<div class="links"><a href="{url}">{mark}Source on GitHub</a><a href="{app_id}.flatpakref">Install file (.flatpakref)</a></div>
</div>
</div>"""


def main():
    apps_file, repo_dir, base_url, readme = sys.argv[1:5]
    repo_dir = Path(repo_dir)
    base_url = base_url.rstrip("/") + "/"
    ids = app_ids(repo_dir)
    source_url = source_repo_url(base_url)

    entries = []
    for repo, prefix in read_apps(apps_file):
        if prefix not in ids:
            print(f"::warning::{prefix} is not in the repository; left out of the directory.", file=sys.stderr)
            continue
        info = github_info(repo)
        if info is None:
            continue
        app_id, ref = ids[prefix]
        entries.append({
            "name": prefix,
            "app_id": app_id,
            "icon": extract_icon(repo_dir, ref, app_id, repo_dir / "icons"),
            **info,
        })

    cards = []
    for entry in entries:
        icon = (f'<img src="{html.escape(entry["icon"])}" alt="">' if entry["icon"]
                else html.escape(entry["name"][:1].upper()))
        cards.append(APP.format(
            icon=icon,
            name=html.escape(entry["name"]),
            version=html.escape(entry["version"]),
            description=html.escape(entry["description"] or "No description yet."),
            app_id=html.escape(entry["app_id"]),
            url=html.escape(entry["url"]),
            remote=REMOTE_NAME,
            mark=GITHUB_MARK,
        ))
    assets = Path(__file__).resolve().parent.parent / "assets"
    if assets.is_dir():
        for asset in assets.iterdir():
            if asset.is_file():
                shutil.copy(asset, repo_dir / asset.name)
    else:
        print(f"::warning::{assets} not found; no logo or favicon.", file=sys.stderr)
    (repo_dir / "index.html").write_text(PAGE.format(
        title=html.escape(TITLE), subtitle=html.escape(SUBTITLE), remote=REMOTE_NAME, base_url=base_url,
        source_url=html.escape(source_url), mark=GITHUB_MARK,
        apps="\n".join(cards) or '<p>No apps yet.</p>',
    ))

    lines = ["| App | Description | Install |", "| --- | --- | --- |"]
    for entry in entries:
        description = html.escape(entry["description"] or "No description yet.", quote=False).replace("|", "\\|")
        lines.append(
            f"| [{entry['name']}]({entry['url']}) {entry['version']} | {description} | "
            f"`flatpak install --user {REMOTE_NAME} {entry['app_id']}` |"
        )
    text = Path(readme).read_text()
    start, end = "<!-- apps:start -->", "<!-- apps:end -->"
    if start in text and end in text:
        head, rest = text.split(start, 1)
        _, tail = rest.split(end, 1)
        Path(readme).write_text(f"{head}{start}\n" + "\n".join(lines) + f"\n{end}{tail}")
    else:
        print("::warning::README.md has no apps:start/apps:end markers; not updated.", file=sys.stderr)


if __name__ == "__main__":
    main()
