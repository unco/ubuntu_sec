"""Build the prototype pages from copies of the real ubuntu.com pages in source/.

  source/CVE-2026-98432.html  browser "Save page as" copy  -> index.html
  source/notices.html         curl of /security/notices     -> notices.html
  source/USN-9027-2.html      curl of /security/notices/USN-9027-2 -> USN-9027-2.html

Each page has tracking, analytics, cookie banner and live chat stripped, assets
pointed at assets/, a prototype banner added, and the proposed changes from
partials/ swapped in. Links between the three pages stay inside the demo.

Usage: python3 tools/build.py
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "source"
PARTIALS = ROOT / "partials"
UBUNTU = "https://ubuntu.com"


def partial(name):
    return (PARTIALS / name).read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------- shared steps

def strip_tracking(html):
    # Everything after the footer is injected tracking/chat/cookie markup.
    html = html.partition("</footer>")[0] + "</footer>\n"
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", "", html, flags=re.S | re.I)
    html = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "", html, flags=re.S | re.I)
    # Drop all HTML comments (one in <head> mentions "<body>", which would
    # otherwise catch the prototype banner).
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    html = re.sub(r"<link[^>]*cookie-policy\.css[^>]*>", "", html)
    # Hints for services we no longer load.
    html = re.sub(r'<link rel="(?:preconnect|manifest|describedby|alternate|canonical)"[^>]*>\s*', "", html, flags=re.S)
    return html


def absolutize(html):
    """Root-relative links only work on ubuntu.com; make them absolute."""
    return re.sub(r'(\s(?:href|src|action))=(["\']?)/(?!/)', r"\1=\2" + UBUNTU + "/", html)


def local_fonts(html):
    # The inline @font-face rules and the preload point at ubuntu.com/static/fonts,
    # which is blocked by CORS anywhere else. Use the copies in assets/fonts.
    fonts = {
        "ubuntu-variable-latin.woff2": "ubuntu-latin.woff2",
        "ubuntu-variable-latin-italic.woff2": "ubuntu-italic-latin.woff2",
        "ubuntu-mono-variable.woff2": "ubuntu-mono-latin.woff2",
    }
    for name, local in fonts.items():
        html = re.sub(
            r"(?:https://ubuntu\.com)?/static/fonts/" + re.escape(name) + r"(?:\?v=\w+)?",
            "assets/fonts/" + local,
            html,
        )
    if "/static/fonts/" in html:
        print("warning: unresolved /static/fonts/ refs remain")
    return html


def local_styles(html, extra_css=()):
    html = re.sub(r'href="[^"]*/styles\.css(?:\?[^"]*)?"', 'href="assets/css/styles.css"', html)
    html = re.sub(r'href="[^"]*/print\.css(?:\?[^"]*)?"', 'href="assets/css/print.css"', html)
    links = "".join(
        f'<link rel="stylesheet" type="text/css" media="screen" href="assets/css/{name}">\n    '
        for name in extra_css
    )
    return html.replace("</head>", links + "</head>", 1)


def local_links(html):
    """Keep navigation between the three demo pages inside the demo."""
    end = r'(?=["#?])'
    html = re.sub(re.escape(UBUNTU + "/security/CVE-2026-98432") + end, "index.html", html)
    html = re.sub(re.escape(UBUNTU + "/security/notices/USN-9027-2") + end, "USN-9027-2.html", html)
    html = re.sub(re.escape(UBUNTU + "/security/notices") + end, "notices.html", html)
    html = html.replace('href="index.html#', 'href="#') if 'id="status"' in html else html
    return html


def mark_prototype(html, what, real_url):
    """Banner and noindex so a public copy can't pass for the real page."""
    html = html.replace("<head>", '<head>\n    <meta name="robots" content="noindex, nofollow">', 1)
    banner = (
        '<div style="background:#262626;color:#fff;padding:.4rem 1.5rem;font-size:.875rem;line-height:1.5">'
        f"Design prototype of {what}, not live security data. "
        f'See the real page at <a style="color:#fff;text-decoration:underline" href="{real_url}">'
        f'{real_url.replace("https://", "")}</a>.'
        "</div>"
    )
    return re.sub(r"(<body\b[^>]*>)", lambda m: m.group(1) + "\n" + banner, html, count=1)


def add_scripts(html, names):
    return html + "".join(f'<script src="assets/js/{n}" defer></script>\n' for n in names) + \
        "</body>\n</html>\n"


def write(name, html):
    (ROOT / name).write_text(html, encoding="utf-8")
    print(f"wrote {name} ({len(html):,} bytes)")


def between(html, start_marker, end_marker, start_from=0):
    a = html.index(start_marker, start_from)
    b = html.index(end_marker, a)
    return a, b


# ---------------------------------------------------------------- CVE page

cve = (SRC / "CVE-2026-98432.html").read_text(encoding="utf-8", errors="replace")
html = strip_tracking(cve)
html = local_fonts(html)

files_dir = re.escape("./CVE-2026-98432 _ Ubuntu_files/")
saved_assets = {
    "styles.css": "assets/css/styles.css",
    "print.css": "assets/css/print.css",
    "CoF_white.svg": "assets/img/CoF_white.svg",
    "display_arrow_cta.png": "assets/img/display_arrow_cta.png",
    "https___assets.ubuntu.com_v1_c96f27b9-CVE-Priority-icon-Critical.svg":
        "assets/img/CVE-Priority-icon-Critical.svg",
}
for name, local in saved_assets.items():
    html = re.sub(files_dir + re.escape(name), local, html)
leftover = re.findall(files_dir + r"[^\"')\s]*", html)
if leftover:
    print("warning: unresolved saved-page refs:", sorted(set(leftover)))

# The CVE copy was saved from a browser, so its global navigation dropdowns are
# already filled in. Reuse that header on the other pages (it is loaded by
# script from ubuntu.com otherwise, which fails off-site).
hdr_start = html.index("<header")
hdr_end = html.rindex("<div", 0, html.index('id="secondary-navigation"'))
GLOBAL_HEADER = html[hdr_start:hdr_end]


def swap_after_heading(html, heading_id, name):
    """Replace the first <p>...</p> after a section heading with a partial."""
    h = html.index(f'id="{heading_id}"')
    start = html.index("<p", h)
    end = html.index("</p>", start) + len("</p>")
    return html[:start] + partial(name) + html[end:]


html = swap_after_heading(html, "description", "description.html")
html = swap_after_heading(html, "mitigation", "mitigation.html")

# Status: from the heading row to the end of the original status table.
status_h2 = html.index('id="status"')
start = html.rindex('<div class="u-fixed-width p-section--shallow"', 0, status_h2)
end = html.index("</table>", status_h2)
end = html.index("</div>", end) + len("</div>")
html = html[:start] + partial("status.html") + html[end:]

html = local_styles(html, ["status.css", "mitigation.css"])
html = local_links(html)
html = mark_prototype(html, "a proposed CVE page", UBUNTU + "/security/CVE-2026-98432")
html = add_scripts(html, ["navigation.js", "dynamic-toc.js", "cve-detail.js", "notices.js", "status.js"])
write("index.html", html)


# ---------------------------------------------------------------- shared for notices pages

def notices_common(raw):
    html = strip_tracking(raw)
    html = absolutize(html)
    html = local_fonts(html)
    # "Further reading" is filled from the Ubuntu blog by script; without it the
    # spinner never stops. Point at the security tag instead.
    html = re.sub(
        r'<li class="p-list__item">\s*<i class="p-icon--spinner[^>]*>Loading\.\.\.</i>\s*</li>',
        '<li class="p-list__item"><a href="https://ubuntu.com/blog/tag/security">Security articles on the Ubuntu blog</a></li>',
        html,
    )
    # Swap in the pre-rendered global header (keeps this page's secondary nav).
    a = html.index("<header")
    b = html.rindex("<div", 0, html.index('id="secondary-navigation"'))
    return html[:a] + GLOBAL_HEADER + html[b:]


# ---------------------------------------------------------------- notices list

html = notices_common((SRC / "notices.html").read_text(encoding="utf-8", errors="replace"))

# Intro: say that candidate fixes are listed too.
intro_end = html.index("</p>", html.index("Developers issue an Ubuntu Security Notice")) + len("</p>")
html = html[:intro_end] + "\n      " + partial("notices-intro.html") + html[intro_end:]

# Subscribe: add the candidate fixes feed.
rss = html.index(">RSS</a>") + len(">RSS</a>")
html = html[:rss] + "\n        " + partial("notices-subscribe.html") + html[rss:]

# Results: alert + tabs above, released notices in one panel, candidates in another.
res_start = html.index('<p class="p-text--small-caps">', html.index('id="notices-list"'))
pag = html.index('<ol class="p-pagination', res_start)
res_end = html.index("</div>", html.index("</ol>", pag)) + len("</div>")  # pagination wrapper
released = html[res_start:res_end]
html = (
    html[:res_start]
    + partial("notices-tabs.html")
    + '\n<div id="released-panel" role="tabpanel" aria-labelledby="tab-released">\n'
    + released
    + "\n</div>\n"
    + partial("notices-candidates.html")
    + html[res_end:]
)

html = local_styles(html, ["notices-proposal.css"])
html = local_links(html)
html = mark_prototype(html, "a proposed Security Notices page", UBUNTU + "/security/notices")
html = add_scripts(html, ["navigation.js", "side-navigation.js", "notices-tabs.js"])
write("notices.html", html)


# ---------------------------------------------------------------- USN-9027-2

html = notices_common((SRC / "USN-9027-2.html").read_text(encoding="utf-8", errors="replace"))

# Hero: one extra row pointing at the timeline.
hero_rel = html.index('<p class="p-heading--5 u-no-margin--bottom">Releases</p>')
hero_row = html.rindex('<div class="row">', 0, hero_rel)
html = html[:hero_row] + partial("usn-hero-row.html") + "\n          " + html[hero_row:]

# Side navigation: two new entries after Update instructions.
nav = html.index('href="#update-instructions">Update instructions</a>')
nav = html.index("</li>", nav) + len("</li>")
html = html[:nav] + "\n" + partial("usn-sidenav.html") + html[nav:]

# New sections after the update instructions table, before the Ubuntu Pro block.
pro = html.index("<h3>Reduce your security exposure</h3>")
pro = html.rindex('<div class="p-section">', 0, pro)
html = html[:pro] + partial("usn-in-progress.html") + "\n" + partial("usn-timeline.html") + "\n          " + html[pro:]

html = local_styles(html, ["notices-proposal.css"])
html = local_links(html)
html = mark_prototype(html, "a proposed security notice page", UBUNTU + "/security/notices/USN-9027-2")
html = add_scripts(html, ["navigation.js", "dynamic-toc.js", "notices.js"])
write("USN-9027-2.html", html)
