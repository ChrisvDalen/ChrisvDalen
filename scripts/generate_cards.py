#!/usr/bin/env python3
"""Generate the profile README stat cards as self-hosted SVGs.

Runs in CI with the repo's default token:
    GITHUB_TOKEN=... GITHUB_USER=ChrisvDalen python3 scripts/generate_cards.py dist
"""
import json
import math
import os
import sys
import urllib.request

ACCENT1 = "#7C3AED"
ACCENT2 = "#06b6d4"
BG = "#0d1117"
TITLE = "#7C3AED"
LABEL = "#c9d1d9"
MUTED = "#8b949e"
FONT = "'Segoe UI',Ubuntu,'Helvetica Neue',sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name
    contributionsCollection {
      totalCommitContributions
      contributionCalendar { totalContributions }
    }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fetch(token, login):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors"):
        raise SystemExit(f"GraphQL errors: {data['errors']}")
    return data["data"]["user"]


def svg_wrap(width, height, css, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
        f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0%" stop-color="{ACCENT1}"/><stop offset="100%" stop-color="{ACCENT2}"/>'
        f"</linearGradient></defs>"
        f'<style>{"".join(css)}</style>{"".join(body)}</svg>'
    )


def render_stats(title, rows, ring_value, ring_label):
    width, height = 495, 200
    r = 50
    c = 2 * math.pi * r
    css = [
        ".t{font:600 18px %s;fill:%s}" % (FONT, TITLE),
        ".l{font:400 14px %s;fill:%s}" % (FONT, LABEL),
        ".v{font:600 14px %s;fill:%s}" % (FONT, ACCENT2),
        ".n{font:700 26px %s;fill:#ffffff}" % FONT,
        ".m{font:400 11px %s;fill:%s}" % (FONT, MUTED),
        ".row{opacity:0;animation:fade .5s ease-out forwards}",
        "@keyframes fade{to{opacity:1}}",
        ".ring{stroke-dasharray:%.2f;stroke-dashoffset:%.2f;animation:ring 1.2s ease-out .3s forwards}" % (c, c),
        "@keyframes ring{to{stroke-dashoffset:%.2f}}" % (c * 0.22),
    ]
    body = [
        f'<rect width="{width}" height="{height}" rx="8" fill="{BG}"/>',
        f'<text class="t" x="25" y="36">{esc(title)}</text>',
    ]
    y = 74
    for i, (label, value) in enumerate(rows):
        css.append(".r%d{animation-delay:%.2fs}" % (i, 0.15 + i * 0.1))
        body.append(
            f'<g class="row r{i}">'
            f'<circle cx="29" cy="{y - 4}" r="3" fill="url(#ac)"/>'
            f'<text class="l" x="42" y="{y}">{esc(label)}</text>'
            f'<text class="v" x="310" y="{y}" text-anchor="end">{esc(value)}</text></g>'
        )
        y += 26
    cx, cy = 405, 106
    body.append(
        f'<g transform="rotate(-90 {cx} {cy})">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" stroke="#21262d" stroke-width="9" fill="none"/>'
        f'<circle class="ring" cx="{cx}" cy="{cy}" r="{r}" stroke="url(#ac)" '
        f'stroke-width="9" stroke-linecap="round" fill="none"/></g>'
    )
    body.append(f'<text class="n" x="{cx}" y="{cy + 2}" text-anchor="middle">{esc(ring_value)}</text>')
    body.append(f'<text class="m" x="{cx}" y="{cy + 20}" text-anchor="middle">{esc(ring_label)}</text>')
    return svg_wrap(width, height, css, body)


def render_langs(title, langs, show_pct=True):
    width, height = 350, 200
    total = sum(size for _, size, _ in langs) or 1
    css = [
        ".t{font:600 18px %s;fill:%s}" % (FONT, TITLE),
        ".l{font:400 13px %s;fill:%s}" % (FONT, LABEL),
        ".seg{transform-box:fill-box;transform-origin:left;transform:scaleX(0);"
        "animation:grow .9s ease-out .2s forwards}",
        "@keyframes grow{to{transform:scaleX(1)}}",
        ".row{opacity:0;animation:fade .5s ease-out forwards}",
        "@keyframes fade{to{opacity:1}}",
    ]
    bar_x, bar_y, bar_w, bar_h = 25, 56, 300, 10
    body = [
        f'<rect width="{width}" height="{height}" rx="8" fill="{BG}"/>',
        f'<text class="t" x="25" y="36">{esc(title)}</text>',
        f'<clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5"/></clipPath>',
        f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="#21262d"/>',
    ]
    x = float(bar_x)
    for name, size, color in langs:
        w = size / total * bar_w
        body.append(
            f'<rect class="seg" x="{x:.2f}" y="{bar_y}" width="{w:.2f}" height="{bar_h}" '
            f'fill="{color}" clip-path="url(#bar)"/>'
        )
        x += w
    for i, (name, size, color) in enumerate(langs):
        colx = 25 + (i % 2) * 165
        rowy = 96 + (i // 2) * 26
        pct = " %.1f%%" % (size / total * 100) if show_pct else ""
        css.append(".g%d{animation-delay:%.2fs}" % (i, 0.3 + i * 0.08))
        body.append(
            f'<g class="row g{i}"><circle cx="{colx + 4}" cy="{rowy - 4}" r="4" fill="{color}"/>'
            f'<text class="l" x="{colx + 16}" y="{rowy}">{esc(name)}{pct}</text></g>'
        )
    return svg_wrap(width, height, css, body)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "dist"
    token = os.environ["GITHUB_TOKEN"]
    login = os.environ["GITHUB_USER"]
    user = fetch(token, login)

    repos = user["repositories"]["nodes"]
    stars = sum(n["stargazerCount"] for n in repos)
    langs = {}
    for node in repos:
        for edge in node["languages"]["edges"]:
            name = edge["node"]["name"]
            size, color = langs.get(name, (0, edge["node"]["color"] or "#8b949e"))
            langs[name] = (size + edge["size"], color)
    top = sorted(((n, s, c) for n, (s, c) in langs.items()), key=lambda t: -t[1])[:6]

    cc = user["contributionsCollection"]
    display = user["name"] or login
    rows = [
        ("Total Stars", stars),
        ("Commits (past year)", cc["totalCommitContributions"]),
        ("Pull Requests", user["pullRequests"]["totalCount"]),
        ("Issues", user["issues"]["totalCount"]),
        ("Contributed To", user["repositoriesContributedTo"]["totalCount"]),
    ]

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "stats-card.svg"), "w") as f:
        f.write(render_stats(f"{display}'s GitHub Stats", rows,
                             cc["contributionCalendar"]["totalContributions"], "past year"))
    with open(os.path.join(out_dir, "top-langs.svg"), "w") as f:
        f.write(render_langs("Most Used Languages", top))
    print("wrote stats-card.svg and top-langs.svg to", out_dir)


if __name__ == "__main__":
    main()
