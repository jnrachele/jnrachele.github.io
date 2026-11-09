#!/usr/bin/env python3
"""Builds the website from site_data.py and publications.txt.

In the GitHub repository this folder is _source/, and the site lives one level up:
    cd _source && python3 build.py ..
"""
import csv, html, random, re, shutil, sys
from datetime import date
from pathlib import Path

from site_data import PROFILE, GRANTS, REPORTS, MEDIA

SRC = Path(__file__).parent
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else SRC.parent / "site"
WIX_PREFIX = "https://www.jnrachele.com/_files/ugd/"

e = html.escape
manifest = {}  # wix url -> local path


def slug(text, n=6):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:n])


def local_file(url, folder, name):
    """Map a Wix-hosted file to a stable local path (recorded in the manifest)."""
    if not url.startswith(WIX_PREFIX):
        return url
    if url in manifest:
        return manifest[url]
    ext = url.rsplit(".", 1)[-1].split("?")[0]
    path = f"files/{folder}/{name}.{ext}"
    i = 2
    while path in manifest.values():
        path = f"files/{folder}/{name}-{i}.{ext}"; i += 1
    manifest[url] = path
    return path


OWN_NAME = re.compile(r"(Rachele, ?J\. ?N\.|Rachele, Jerome Nikolaos|Rachele J\.N\.)")


def cite_html(text):
    return OWN_NAME.sub(r"<strong>\1</strong>", e(text, quote=False))


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
        m = re.search(r"\((\d{4})\)", cite)
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
    parts = []
    for label, href in links:
        ext = href.startswith("http")
        attrs = ' rel="noopener"' if ext else ""
        parts.append(f'<a href="{e(href)}"{attrs}>{e(label)}</a>')
    return f'<span class="links">{"".join(parts)}</span>'


def pub_item(p):
    return (f'<li class="pub"><p>{cite_html(p["cite"])}</p>{links_html(p["links"])}</li>')


# ---------- the map ----------
def neighbourhood_map(seed=7):
    """An illustrative street grid, blocks shaded like an area-disadvantage choropleth."""
    rnd = random.Random(seed)
    ramp = ["#e3ebe4", "#cfddd2", "#b8cdbe", "#9fbca9", "#86aa94",
            "#6c977f", "#53836b", "#3c6e58", "#285a47", "#183f33"]
    W = H = 480
    cols = [0]
    while cols[-1] < W:
        cols.append(cols[-1] + rnd.choice([34, 40, 46, 52, 58]))
    rows = [0]
    while rows[-1] < H:
        rows.append(rows[-1] + rnd.choice([30, 36, 42, 48]))
    gap = 5
    rects = []
    for ci in range(len(cols) - 1):
        for ri in range(len(rows) - 1):
            x, y = cols[ci] + gap / 2, rows[ri] + gap / 2
            w, h = cols[ci + 1] - cols[ci] - gap, rows[ri + 1] - rows[ri] - gap
            cx, cy = x + w / 2, y + h / 2
            # disadvantage rises toward the outer south-west, with local noise
            d = (cx / W) * 0.35 + ((H - cy) / H) * 0.15
            d = 1 - d + rnd.uniform(-0.14, 0.14)
            park = (cx - 330) ** 2 + (cy - 140) ** 2 < 70 ** 2 and rnd.random() < 0.6
            rects.append([x, y, w, h, None if park else d])
    # rank areas into true deciles, as SEIFA does
    scored = sorted((r for r in rects if r[4] is not None), key=lambda r: r[4])
    for i, r in enumerate(scored):
        r[4] = ramp[i * 10 // len(scored)]
    rects = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{f or 'var(--park)'}"/>'
             for x, y, w, h, f in rects]
    road = (f'<path d="M-10 {H*0.82:.0f} L{W+10} {H*0.18:.0f}" stroke="var(--paper)" '
            f'stroke-width="9" fill="none"/>'
            f'<path d="M{W*0.62:.0f} -10 C {W*0.55:.0f} {H*0.4:.0f}, {W*0.75:.0f} {H*0.6:.0f}, {W*0.68:.0f} {H+10}" '
            f'stroke="var(--paper)" stroke-width="6" fill="none"/>')
    legend = "".join(f'<span style="background:{c}"></span>' for c in ramp)
    svg = (f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="map-cap" preserveAspectRatio="xMidYMid slice">'
           f'{"".join(rects)}{road}</svg>')
    return svg, legend


# ---------- page shell ----------
NAV = [("index.html", "Home"), ("academic-publications.html", "Publications"),
       ("grants.html", "Grants"), ("reports.html", "Reports"), ("media.html", "Media")]


def page(filename, title, body, description, main_class=""):
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if href == filename else ""}>{label}</a>'
        for href, label in NAV)
    full_title = f"{title} | {PROFILE['name']}" if title else f"{PROFILE['name']} | Social epidemiologist"
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
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;800&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap">
<link rel="stylesheet" href="styles.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <a class="wordmark" href="index.html">{e(PROFILE['short'])}</a>
  <nav aria-label="Main">{nav}</nav>
</header>
<main id="main" class="{main_class}">
{body}
</main>
<footer class="site-footer">
  <p><a href="mailto:{PROFILE['email']}">{PROFILE['email']}</a></p>
  <p><a href="{PROFILE['linkedin']}" rel="noopener">LinkedIn</a> <a href="{PROFILE['twitter']}" rel="noopener">X / Twitter</a></p>
  <p class="small">© {date.today().year} Jerome N Rachele</p>
</footer>
</body>
</html>
"""


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "styles.css", OUT / "styles.css")
    shutil.copy(SRC / "favicon.svg", OUT / "favicon.svg")
    manifest[PROFILE["photo_src"]] = PROFILE["photo"]

    sections = parse_publications()
    refereed = sections[0]["items"]
    total = sum(len(s["items"]) for s in sections)

    # ---- home
    svg, legend = neighbourhood_map()
    recent = "".join(pub_item(p) for p in refereed[:4])
    home = f"""
<section class="hero">
  <div class="hero-text">
    <img class="portrait" src="{PROFILE['photo']}" alt="Portrait of Jerome Rachele" width="96" height="104" onerror="this.remove()">
    <h1>{e(PROFILE['name'])}</h1>
    <p class="lede">{e(PROFILE['statement'])}</p>
    <p class="role">{e(PROFILE['role'])}</p>
    <p class="contact"><a class="button" href="mailto:{PROFILE['email']}">Email me</a>
       <a href="{PROFILE['linkedin']}" rel="noopener">LinkedIn</a>
       <a href="{PROFILE['twitter']}" rel="noopener">X / Twitter</a></p>
  </div>
  <figure class="map">
    {svg}
    <figcaption id="map-cap"><span class="legend" aria-hidden="true">{legend}</span>
      Neighbourhoods shaded from least to most disadvantaged. An illustration, not real data.</figcaption>
  </figure>
</section>
<section class="recent">
  <h2>Recent publications</h2>
  <ol class="pubs">{recent}</ol>
  <p><a href="academic-publications.html">All {total} publications</a></p>
</section>
<section class="elsewhere">
  <div><h2><a href="grants.html">Grants</a></h2><p>{len(GRANTS)} funded projects on inclusive cities, disability and neighbourhood health.</p></div>
  <div><h2><a href="reports.html">Reports</a></h2><p>Research reports for government, including annual SEIFA data for 1996–2021.</p></div>
  <div><h2><a href="media.html">Media</a></h2><p>Radio interviews, podcasts and articles for The Conversation.</p></div>
</section>
"""
    (OUT / "index.html").write_text(page("index.html", "", home,
        PROFILE["statement"] + " " + PROFILE["role"] + ".", "home"), encoding="utf-8")

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
                for y, ps in years.items())
        else:
            inner = f'<ol class="pubs">{"".join(pub_item(p) for p in s["items"])}</ol>'
        blocks.append(f'<section class="pub-section" id="{sid}"><h2>{e(s["title"])} <span class="count">{len(s["items"])}</span></h2>{inner}</section>')
    jump = "".join(f'<a href="#{slug(s["title"],3)}">{e(s["title"])}</a>' for s in sections)
    pubs_body = f"""
<header class="page-head">
  <h1>Publications</h1>
  <p class="jump">{jump}</p>
  <div class="filter">
    <label for="q">Search by title, author or journal</label>
    <input id="q" type="search" autocomplete="off" placeholder="e.g. walkability, HABITAT, Health &amp; Place">
    <p class="status" id="status" aria-live="polite"></p>
  </div>
</header>
{"".join(blocks)}
<script>
(() => {{
  const q = document.getElementById('q'), status = document.getElementById('status');
  const items = [...document.querySelectorAll('.pub')];
  q.addEventListener('input', () => {{
    const terms = q.value.toLowerCase().split(/\\s+/).filter(Boolean);
    let shown = 0;
    items.forEach(li => {{
      const t = li.textContent.toLowerCase();
      const ok = terms.every(w => t.includes(w));
      li.hidden = !ok; if (ok) shown++;
    }});
    document.querySelectorAll('.year-group, .pub-section').forEach(g =>
      g.hidden = !g.querySelector('.pub:not([hidden])'));
    status.textContent = terms.length ? (shown ? `${{shown}} of ${{items.length}} match` : 'No matches. Try a shorter word.') : '';
  }});
}})();
</script>
"""
    (OUT / "academic-publications.html").write_text(page("academic-publications.html", "Publications", pubs_body,
        f"Refereed publications, reviews, book chapters and thesis of {PROFILE['name']}."), encoding="utf-8")

    # ---- grants
    total_amt = sum(g["amount"] for g in GRANTS)
    rows = "".join(f"""
<li class="grant">
  <div><h2>{e(g['title'])}</h2>
  <p class="funder">{e(g['funder'])}</p>
  <p class="meta">{cite_html(g['team'])}<br>{e(g['dates'])}</p></div>
  <p class="amount">${g['amount']:,}</p>
</li>""" for g in GRANTS)
    grants_body = f"""
<header class="page-head"><h1>Grants</h1></header>
<ol class="grants">{rows}</ol>
<p class="grant-total"><span>Total funding</span> <span class="amount">${total_amt:,}</span></p>
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
                if len(lk) > 2:
                    manifest[url] = lk[2]; url = lk[2]
                else:
                    m = re.search(r"\((\d{4})\)\.?\s*(.*)", cite)
                    url = local_file(url, "reports", f"{m.group(1)}-{slug(m.group(2))}")
            out.append((label, url))
        ritems.append(f'<li class="pub"><p>{cite_html(cite)}</p>{links_html(out)}</li>')
    reports_body = f"""
<header class="page-head"><h1>Reports</h1></header>
<ol class="pubs plain">{"".join(ritems)}</ol>
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
            t = f'<a href="{e(url)}"{" rel=\"noopener\"" if url.startswith("http") else ""}>{e(title)}</a>' if url else e(title)
            meta = "".join(x for x in [e(outlet), f"<time>{e(when)}</time>" if when else ""] if x)
            lis.append(f'<li><p class="media-meta">{meta}</p><h3>{t}</h3>{f"<p class=note>{e(note)}</p>" if note else ""}</li>')
        groups.append(f'<section class="media-group"><h2>{e(group)}</h2><ul class="media">{"".join(lis)}</ul></section>')
    media_body = f"""
<header class="page-head"><h1>Media</h1></header>
{"".join(groups)}
"""
    (OUT / "media.html").write_text(page("media.html", "Media", media_body,
        f"Radio, podcast and press appearances by {PROFILE['name']}."), encoding="utf-8")

    # ---- 404
    (OUT / "404.html").write_text(page("404.html", "Page not found",
        '<header class="page-head"><h1>Page not found</h1></header><p class="prose">This page has moved or no longer exists. Try the <a href="index.html">home page</a> or the <a href="academic-publications.html">publications list</a>.</p>',
        "Page not found."), encoding="utf-8")

    # ---- file manifest for the download scripts
    with open(OUT / "file-manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["url", "path"])
        for url, path in manifest.items():
            w.writerow([url, path])
    print(f"Built {OUT}  ({total} publications, {len(manifest)} files to download)")


if __name__ == "__main__":
    build()
