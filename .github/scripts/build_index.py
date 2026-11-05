"""Build index.json — every world on the shelf, with its stars — and give each world its issue to star.

Run by the shelf's Action on every merge and every hour. Needs nothing but the standard library and GITHUB_TOKEN.
A star is a 👍 on a world's issue; the issue says which world it is in a hidden line (<!-- slug: … -->).
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GITHUB_TOKEN"]


def gh(method: str, path: str, body: dict | None = None):
    req = urllib.request.Request(f"https://api.github.com{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"null")


def issues() -> dict[str, dict]:
    out, page = {}, 1
    while True:
        got = gh("GET", f"/repos/{REPO}/issues?labels=world&state=all&per_page=100&page={page}")
        for i in got:
            m = re.search(r"<!-- slug: ([a-z0-9-]+) -->", i.get("body") or "")
            if m:
                out[m.group(1)] = {"issue": i["number"], "stars": (i.get("reactions") or {}).get("+1", 0)}
        if len(got) < 100:
            return out
        page += 1


def main() -> None:
    try:
        gh("POST", f"/repos/{REPO}/labels", {"name": "world", "color": "2de2d0", "description": "a world on the shelf: 👍 it to star it"})
    except Exception:  # noqa: BLE001 — it is there already
        pass
    known = issues()
    cards = []
    for f in sorted(Path("worlds").glob("*/card.json")):
        c = json.loads(f.read_text())
        if c["slug"] not in known:
            i = gh("POST", f"/repos/{REPO}/issues", {"title": f"★ {c['title']}", "labels": ["world"],
                   "body": f"{c.get('question') or c.get('line') or ''}\n\nGive this a 👍 to star it — or star it from SPOCK's Community shelf.\n\n<!-- slug: {c['slug']} -->"})
            known[c["slug"]] = {"issue": i["number"], "stars": 0}
        cards.append({**c, **known[c["slug"]]})
    cards.sort(key=lambda c: (c.get("updated", ""), c["title"]), reverse=True)
    new = json.dumps({"shelf": "community", "worlds": cards}, indent=1, ensure_ascii=False) + "\n"
    p = Path("index.json")
    if not p.exists() or p.read_text() != new:
        p.write_text(new)
        print("index.json changed")


if __name__ == "__main__":
    main()
