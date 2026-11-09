#!/usr/bin/env python3
"""Builds the website from site_data.py and publications.txt.

In the GitHub repository this folder is _source/, and the site lives one level up:
    cd _source && python3 build.py ..
"""
import csv, html, random, re, shutil, sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

from site_data import (PROFILE, METRICS, THEMES, GRANTS, REPORTS, MEDIA, AWARDS,
                       SUPERVISION, EDUCATION, SERVICE, TALKS)

SRC = Path(__file__).parent
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else SRC.parent / "site"
WIX_PREFIX = "https://www.jnrachele.com/_files/ugd/"

e = html.escape
manifest = {}  # wix url -> local path (kept stable once files are in the repo)
if (OUT / "file-manifest.csv").exists():
    for row in csv.DictReader(open(OUT / "file-manifest.csv", encoding="utf-8")):
        manifest[row["url"]] = row["path"]

THEME_COLOURS = {"disadvantage": "var(--signal)", "design": "var(--sun)", "inclusion": "var(--mint)"}


def slug(text, n=6):
    return "-".join(re.findall(r"[a-z0-9]+", text.lower())[:n])


def local_file(url, folder, name):
    if not url.startswith(WIX_PREFIX):
        return url
    if url in manifest:
        return manifest[url]
    ext = url.rsplit(".", 1)[-1].split("?")[0]
    path, i = f"files/{folder}/{name}.{ext}", 2
    while path in manifest.values():
        path = f"files/{folder}/{name}-{i}.{ext}"; i += 1
    manifest[url] = path
    return path


OWN_NAME = re.compile(r"(Rachele, ?J\.(?: ?N\.?)?|Rachele, Jerome Nikolaos|Rachele J\. ?N\.)")


def cite_html(text):
    return OWN_NAME.sub(r"<strong>\1</strong>", e(text, quote=False))


def ext_attr(href):
    return ' rel="noopener"' if href.startswith("http") else ""


# ---------- publications ----------
def parse_publications():
    sections, current = [], None
    for line in (SRC / "publications.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("# "):
            continue
        if line.startswith("## "):
            current = {"title": line[3:], "items": []}
            sections.append(current)
            continue
        cite, _, links = line.partition("||")
        cite = cite.strip()
        m = re.search(r"\((?:[^()]*?)(\d{4})[^()]*\)", cite)
        year = m.group(1) if m else ""
        after = cite[m.end():].lstrip(". ") if m else cite
        title = re.split(r"(?<=[.?])\s", after, maxsplit=1)[0]
        surname = re.split(r"[ ,]", cite, maxsplit=1)[0]
        out_links = []
        for url in links.split():
            if url.startswith(WIX_PREFIX):
                out_links.append(("PDF", local_file(url, "papers", f"{year}-{slug(surname,1)}-{slug(title)}")))
            elif "doi.org" in url:
                out_links.append(("DOI", url))
            else:
                out_links.append(("Link", url))
        current["items"].append({"cite": cite, "year": year, "links": out_links})
    return sections


def links_html(links):
    if not links:
        return ""
    return '<span class="links">' + "".join(
        f'<a href="{e(h)}"{ext_attr(h)}>{e(l)}</a>' for l, h in links) + "</span>"


def pub_item(p, show_year=False):
    yr = f'<span class="yr">{p["year"]}</span>' if show_year else ""
    return f'<li class="pub">{yr}<p>{cite_html(p["cite"])}</p>{links_html(p["links"])}</li>'


# ---------- the map ----------
def city_map(W=1600, H=720, seed=11, routes=True):
    """Street grid shaded like an area-disadvantage choropleth, crossed by three
    'transit lines', one per research theme."""
    rnd = random.Random(seed)
    ramp = ["#16505a", "#145059", "#134a53", "#11444d", "#0f3e47",
            "#0e3941", "#0c343c", "#0b2f37", "#0a2b32", "#09272e"]
    cols = [0]
    while cols[-1] < W:
        cols.append(cols[-1] + rnd.choice([48, 56, 64, 72, 88]))
    rows = [0]
    while rows[-1] < H:
        rows.append(rows[-1] + rnd.choice([40, 48, 56, 64]))
    gap, cells = 6, []
    for ci in range(len(cols) - 1):
        for ri in range(len(rows) - 1):
            x, y = cols[ci] + gap / 2, rows[ri] + gap / 2
            w, h = cols[ci + 1] - cols[ci] - gap, rows[ri + 1] - rows[ri] - gap
            cx, cy = x + w / 2, y + h / 2
            d = 0.55 * (cx / W) + 0.25 * (1 - cy / H) + rnd.uniform(-0.16, 0.16)
            cells.append([x, y, w, h, d])
    ranked = sorted(cells, key=lambda c: c[4])
    for i, c in enumerate(ranked):
        c[4] = i * 10 // len(ranked)
    rects = "".join(
        f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" fill="{ramp[9 - d]}" '
        f'style="--d:{d}"/>' for x, y, w, h, d in cells)
    lines = ""
    if routes:
        paths = [
            ("disadvantage", f"M{W*0.47:.0f} {H+20} L{W*0.47:.0f} {H*0.62:.0f} L{W*0.60:.0f} {H*0.40:.0f} L{W*0.80:.0f} {H*0.40:.0f} L{W+20} {H*0.12:.0f}"),
            ("design", f"M{W*0.56:.0f} -20 L{W*0.56:.0f} {H*0.22:.0f} L{W*0.68:.0f} {H*0.52:.0f} L{W*0.68:.0f} {H+20}"),
            ("inclusion", f"M{W*0.50:.0f} {H*0.86:.0f} L{W*0.74:.0f} {H*0.86:.0f} L{W*0.88:.0f} {H*0.68:.0f} L{W+20} {H*0.68:.0f}"),
        ]
        stops = [(W*0.60, H*0.40), (W*0.68, H*0.52), (W*0.68, H*0.86), (W*0.80, H*0.40), (W*0.88, H*0.68)]
        lines = "".join(
            f'<path class="route" d="{d}" stroke="{THEME_COLOURS[k]}" pathLength="1"/>' for k, d in paths)
        lines += "".join(
            f'<circle class="stop" cx="{x:.0f}" cy="{y:.0f}" r="9"/>' for x, y in stops)
    return (f'<svg class="citymap" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'<g class="blocks">{rects}</g>{lines}</svg>')


def route_bar():
    return ('<div class="routebar" aria-hidden="true"><span style="background:var(--signal)"></span>'
            '<span style="background:var(--sun)"></span><span style="background:var(--mint)"></span></div>')


# ---------- page shell ----------
NAV = [("index.html", "Home"), ("about.html", "About"), ("academic-publications.html", "Publications"),
       ("grants.html", "Grants"), ("reports.html", "Reports"), ("media.html", "Media")]


def page(filename, title, body, description, hero=""):
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if href == filename else ""}>{label}</a>'
        for href, label in NAV)
    full_title = f"{title} | {PROFILE['name']}" if title else f"{PROFILE['name']} | {PROFILE['title']}"
    if not hero:
        hero = f'<div class="page-band">{city_map(1600, 260, seed=len(title) + 3, routes=False)}<div class="wrap"><h1>{e(title)}</h1></div></div>{route_bar()}'
    return f"""<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:type" content="website">
<meta name="theme-color" content="#0b2f37">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..900&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <a class="wordmark" href="index.html">{e(PROFILE['short'])}</a>
  <nav aria-label="Main">{nav}</nav>
</header>
{hero}
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap foot">
    <div>
      <p class="foot-name">{e(PROFILE['name'])}</p>
      <p>{e(PROFILE['role'])}</p>
    </div>
    <ul class="foot-links">
      <li><a href="mailto:{PROFILE['email']}">{PROFILE['email']}</a></li>
      <li><a href="{PROFILE['scholar']}" rel="noopener">Google Scholar</a></li>
      <li><a href="{PROFILE['linkedin']}" rel="noopener">LinkedIn</a></li>
      <li><a href="{PROFILE['twitter']}" rel="noopener">X / Twitter</a></li>
    </ul>
  </div>
  {route_bar()}
</footer>
</body>
</html>
"""


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "styles.css", OUT / "styles.css")
    shutil.copy(SRC / "favicon.svg", OUT / "favicon.svg")
    manifest.setdefault(PROFILE["photo_src"], PROFILE["photo"])

    sections = parse_publications()
    refereed = sections[0]["items"]
    total = sum(len(s["items"]) for s in sections)
    funding = sum(g["amount"] for g in GRANTS)
    photo = (f'<img class="portrait" src="{PROFILE["photo"]}" alt="Jerome Rachele" '
             f'width="280" height="300" loading="lazy" onerror="this.remove()">')

    # ---- home
    hero = f"""
<section class="hero">
  {city_map()}
  <div class="wrap hero-inner">
    <p class="hero-title">{e(PROFILE['title'])}</p>
    <h1>{e(PROFILE['name'])}</h1>
    <p class="lede">{e(PROFILE['statement'])}</p>
    <p class="cta"><a class="button" href="mailto:{PROFILE['email']}">Get in touch</a>
      <a class="button ghost" href="academic-publications.html">Read the research</a></p>
  </div>
</section>
<section class="legend" aria-label="At a glance">
  <div class="wrap legend-inner">
    <p><b>{total}</b> publications</p>
    <p><b>{METRICS['citations']:,}</b> citations</p>
    <p><b>{METRICS['h_index']}</b> h-index</p>
    <p><b>${funding/1000:,.0f}k</b> research funding</p>
    <p class="asof">Citations from <a href="{PROFILE['scholar']}" rel="noopener">Google Scholar</a>, {METRICS['as_of']}</p>
  </div>
</section>"""
    themes = "".join(f"""
  <article class="theme" style="--c:{THEME_COLOURS[t['key']]}">
    <h3>{e(t['title'])}</h3>
    <p>{e(t['text'])}</p>
    <a href="academic-publications.html?q={quote(t['search'])}">Papers on this</a>
  </article>""" for t in THEMES)
    dated = sorted((p for p in refereed if p["cite"][0].isupper() and ", " in p["cite"][:30]),
                   key=lambda p: p["year"], reverse=True)
    recent = "".join(pub_item(p, show_year=True) for p in dated[:4])
    home = f"""
<section class="wrap block">
  <h2 class="section-title">What I work on</h2>
  <div class="themes">{themes}
  </div>
</section>
<section class="wrap block split">
  <div>
    <h2 class="section-title">Latest publications</h2>
    <ol class="pubs">{recent}</ol>
    <p class="more"><a href="academic-publications.html">All {total} publications</a></p>
  </div>
  <aside class="about-card">
    {photo}
    <p>{e(PROFILE['bio'][0])}</p>
    <p class="more"><a href="about.html">More about me</a></p>
  </aside>
</section>
"""
    (OUT / "index.html").write_text(page("index.html", "", home,
        PROFILE["statement"] + " " + PROFILE["role"] + ".", hero=hero), encoding="utf-8")

    # ---- about
    roles = "".join(f"<li><b>{e(r)}</b><span>{e(o)}</span></li>" for r, o in PROFILE["roles"])
    awards = "".join(f"<li><span class=\"when\">{y}</span><b>{e(a)}</b><span>{e(o)}</span></li>" for a, o, y in AWARDS)
    current = [s for s in SUPERVISION if s[4].endswith("–")]
    past = [s for s in SUPERVISION if not s[4].endswith("–")]
    def sup(rows):
        return "".join(f"""<li><span class="when">{e(y)}</span><b>{e(n)}</b>
          <span class="thesis">{e(t)}</span><span class="meta">{e(deg)}, {e(r.lower())} supervisor, {e(inst)}</span></li>""" for n, deg, r, t, y, inst in rows)
    edu = "".join(f"<li><span class=\"when\">{y}</span><b>{e(q)}</b><span>{e(i)}</span></li>" for q, i, y in EDUCATION)
    svc = "".join(f"<li><span class=\"when\">{e(y)}</span><b>{e(s)}</b></li>" for s, y in SERVICE)
    about = f"""
<section class="wrap block about-top">
  {photo}
  <div class="prose">{"".join(f"<p>{e(p)}</p>" for p in PROFILE['bio'])}
    <p class="cta"><a class="button" href="mailto:{PROFILE['email']}">Email me</a>
      <a class="button ghost dark" href="{PROFILE['scholar']}" rel="noopener">Google Scholar</a>
      <a class="button ghost dark" href="{PROFILE['vu_profile']}" rel="noopener">VU research profile</a></p>
  </div>
</section>
"""
    (OUT / "about.html").write_text(page("about.html", "About", about,
        f"About {PROFILE['name']}, {PROFILE['title']} at Victoria University."), encoding="utf-8")

    # ---- publications
    blocks = []
    for s in sections:
        sid = slug(s["title"], 3)
        if s is sections[0]:
            years = {}
            for p in s["items"]:
                years.setdefault(p["year"], []).append(p)
            inner = "".join(
                f'<div class="year-group"><h3 class="year">{y}</h3><ol class="pubs">{"".join(pub_item(p) for p in ps)}</ol></div>'
                for y, ps in sorted(years.items(), key=lambda kv: kv[0], reverse=True))
        else:
            inner = f'<ol class="pubs">{"".join(pub_item(p) for p in s["items"])}</ol>'
        blocks.append(f'<section class="pub-section" id="{sid}"><h2 class="section-title">{e(s["title"])} <span class="count">{len(s["items"])}</span></h2>{inner}</section>')
    chips = "".join(
        f'<button type="button" class="chip" style="--c:{THEME_COLOURS[t["key"]]}" data-q="{e(t["search"])}">{e(t["title"])}</button>'
        for t in THEMES)
    jump = "".join(f'<a href="#{slug(s["title"],3)}">{e(s["title"])}</a>' for s in sections)
    pubs_body = f"""
<section class="wrap block">
  <div class="filter">
    <label for="q">Search {total} publications by title, author or journal</label>
    <input id="q" type="search" autocomplete="off" placeholder="e.g. walkability, HABITAT, Health &amp; Place">
    <div class="chips" aria-label="Filter by theme">{chips}</div>
    <p class="status" id="status" aria-live="polite"></p>
  </div>
  <p class="jump">{jump} <a href="{PROFILE['scholar']}" rel="noopener">Google Scholar profile</a></p>
  {"".join(blocks)}
</section>
<script>
(() => {{
  const q = document.getElementById('q'), status = document.getElementById('status');
  const items = [...document.querySelectorAll('.pub')], chips = [...document.querySelectorAll('.chip')];
  const run = () => {{
    const terms = q.value.toLowerCase().split(/\\s+/).filter(Boolean);
    let shown = 0;
    items.forEach(li => {{
      const ok = terms.every(w => li.textContent.toLowerCase().includes(w));
      li.hidden = !ok; if (ok) shown++;
    }});
    document.querySelectorAll('.year-group, .pub-section').forEach(g => g.hidden = !g.querySelector('.pub:not([hidden])'));
    chips.forEach(c => c.setAttribute('aria-pressed', String(q.value.trim().toLowerCase() === c.dataset.q)));
    status.textContent = terms.length ? (shown ? `${{shown}} of ${{items.length}} match` : 'No matches. Try a shorter word.') : '';
  }};
  q.addEventListener('input', run);
  chips.forEach(c => c.addEventListener('click', () => {{
    q.value = c.getAttribute('aria-pressed') === 'true' ? '' : c.dataset.q; run();
  }}));
  try {{ const p = new URLSearchParams(location.search).get('q'); if (p) {{ q.value = p; run(); }} }} catch (err) {{}}
}})();
</script>
"""
    (OUT / "academic-publications.html").write_text(page("academic-publications.html", "Publications", pubs_body,
        f"Refereed publications, reviews, book chapters and thesis of {PROFILE['name']}."), encoding="utf-8")

    # ---- grants
    rows = "".join(f"""
<li class="grant">
  <div><h3>{e(g['title'])}</h3>
  <p class="funder">{e(g['funder'])}</p>
  <p class="meta">{cite_html(g['team'])} · {e(g['dates'])}</p></div>
  <p class="amount">${g['amount']:,}</p>
</li>""" for g in GRANTS)
    grants_body = f"""
<section class="wrap block">
  <p class="big-total"><b>${funding:,}</b> in research funding across {len(GRANTS)} grants</p>
  <ol class="grants">{rows}</ol>
</section>
"""
    (OUT / "grants.html").write_text(page("grants.html", "Grants", grants_body,
        f"Research grants awarded to {PROFILE['name']}."), encoding="utf-8")

    # ---- reports
    ritems = []
    for cite, links in REPORTS:
        out = []
        for lk in links:
            label, url = lk[0], lk[1]
            if url.startswith(WIX_PREFIX):
                m = re.search(r"\((\d{4})\)\.?\s*(.*)", cite)
                url = local_file(url, "reports", f"{m.group(1)}-{slug(m.group(2))}")
            out.append((label, url))
        ritems.append(f'<li class="pub"><p>{cite_html(cite)}</p>{links_html(out)}</li>')
    reports_body = f"""
<section class="wrap block">
  <p class="intro">Research reports, policy resources and open data, written for government, industry and community partners.</p>
  <ol class="pubs plain">{"".join(ritems)}</ol>
</section>
"""
    (OUT / "reports.html").write_text(page("reports.html", "Reports", reports_body,
        f"Research reports and datasets by {PROFILE['name']}."), encoding="utf-8")

    # ---- media
    groups = []
    for group, items in MEDIA:
        lis = []
        for outlet, title, when, url, note in items:
            if url and url.startswith(WIX_PREFIX):
                url = local_file(url, "media", slug(outlet, 2) + "-" + slug(title))
            t = f'<a href="{e(url)}"{ext_attr(url)}>{e(title)}</a>' if url else e(title)
            meta = e(outlet) + (f", <time>{e(when)}</time>" if when else "")
            lis.append(f'<li><p class="media-meta">{meta}</p><h3>{t}</h3>{f"<p class=note>{e(note)}</p>" if note else ""}</li>')
        groups.append(f'<section class="media-group"><h2 class="section-title">{e(group)}</h2><ul class="media">{"".join(lis)}</ul></section>')
    talks = "".join(
        f'<li><p class="media-meta">{e(w)}</p><h3>{e(v)}</h3>{f"<p class=note>{e(t)}</p>" if t else ""}</li>'
        for v, t, w in TALKS)
    groups.append(f'<section class="media-group"><h2 class="section-title">Invited talks</h2><ul class="media">{talks}</ul></section>')
    media_body = f'<section class="wrap block media-grid">{"".join(groups)}</section>'
    (OUT / "media.html").write_text(page("media.html", "Media", media_body,
        f"Radio, podcast and press appearances by {PROFILE['name']}."), encoding="utf-8")

    # ---- 404
    (OUT / "404.html").write_text(page("404.html", "Page not found",
        '<section class="wrap block"><p class="intro">This page has moved or no longer exists. Try the <a href="/">home page</a> or the <a href="/academic-publications.html">publications list</a>.</p></section>',
        "Page not found."), encoding="utf-8")

    with open(OUT / "file-manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "path"])
        for url, path in manifest.items():
            w.writerow([url, path])
    print(f"Built {OUT}  ({total} publications, {len(manifest)} files in manifest)")


if __name__ == "__main__":
    build()
