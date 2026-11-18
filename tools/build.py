"""Build index.html from a browser "Save page as" copy of the Ubuntu CVE page.

Strips all tracking, analytics, cookie banner and live chat code, keeps the
markup and styles, and points assets at the local assets/ folder.

Usage: python3 tools/build.py "<path to saved .html>"
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
files_dir = re.escape("./" + pathlib.Path(sys.argv[1]).stem + "_files/")

# Everything after the footer is injected tracking/chat/cookie markup.
head_and_body, _, _ = src.partition("</footer>")
html = head_and_body + "</footer>\n"

# Remove scripts, noscripts, iframes and saved-page comments.
html = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)
html = re.sub(r"<noscript\b[^>]*>.*?</noscript>", "", html, flags=re.S | re.I)
html = re.sub(r"<iframe\b[^>]*>.*?</iframe>", "", html, flags=re.S | re.I)
html = re.sub(r"<!-- saved from url=.*?-->\s*", "", html)
html = re.sub(r'<link[^>]*cookie-policy\.css[^>]*>', "", html)
# Hints for services we no longer load.
html = re.sub(r'<link rel="(?:preconnect|manifest|describedby|alternate)"[^>]*>\s*', "", html)

# Fonts: the inline @font-face rules use root-relative ubuntu.com paths and the
# preload points cross-origin (blocked by CORS off ubuntu.com). Use repo copies.
fonts = {
    "ubuntu-variable-latin.woff2": "ubuntu-latin.woff2",
    "ubuntu-variable-latin-italic.woff2": "ubuntu-italic-latin.woff2",
    "ubuntu-mono-variable.woff2": "ubuntu-mono-latin.woff2",
}
for name, local in fonts.items():
    html = re.sub(
        r'(?:https://ubuntu\.com)?/static/fonts/' + re.escape(name) + r'(?:\?v=\w+)?',
        "assets/fonts/" + local,
        html,
    )
if "/static/fonts/" in html:
    print("warning: unresolved /static/fonts/ refs remain")

# Local asset paths.
assets = {
    "styles.css": "assets/css/styles.css",
    "print.css": "assets/css/print.css",
    "CoF_white.svg": "assets/img/CoF_white.svg",
    "display_arrow_cta.png": "assets/img/display_arrow_cta.png",
    "https___assets.ubuntu.com_v1_c96f27b9-CVE-Priority-icon-Critical.svg":
        "assets/img/CVE-Priority-icon-Critical.svg",
}
for name, local in assets.items():
    html = re.sub(files_dir + re.escape(name), local, html)

leftover = re.findall(files_dir + r"[^\"')\s]*", html)
if leftover:
    print("warning: unresolved saved-page refs:", sorted(set(leftover)))

def swap_after_heading(html, heading_id, partial):
    """Replace the first <p>...</p> after the given section heading with a partial."""
    h = html.index(f'id="{heading_id}"')
    start = html.index("<p", h)
    end = html.index("</p>", start) + len("</p>")
    return html[:start] + (ROOT / "partials" / partial).read_text(encoding="utf-8").strip() + html[end:]


# Rewritten Description and Mitigation text from the status proposal.
html = swap_after_heading(html, "description", "description.html")
html = swap_after_heading(html, "mitigation", "mitigation.html")

# Swap the Status section for the redesigned one in partials/status.html.
# Replaces from the Status heading row to the end of the original status table.
status_h2 = html.index('id="status"')
start = html.rindex('<div class="u-fixed-width p-section--shallow"', 0, status_h2)
end = html.index("</table>", status_h2)
end = html.index("</div>", end) + len("</div>")
html = html[:start] + (ROOT / "partials" / "status.html").read_text(encoding="utf-8") + html[end:]
html = html.replace(
    '<link rel="stylesheet" type="text/css" media="print"',
    '<link rel="stylesheet" type="text/css" media="screen" href="assets/css/status.css">\n'
    '    <link rel="stylesheet" type="text/css" media="print"',
    1,
)

# Mark the page as a prototype so a public copy can't pass for the real advisory.
html = html.replace(
    "<head>",
    '<head>\n    <meta name="robots" content="noindex, nofollow">',
    1,
)
banner = (
    '<div style="background:#262626;color:#fff;padding:.4rem 1.5rem;font-size:.875rem;line-height:1.5">'
    "Design prototype of a proposed status section, not live security data. "
    'See the real advisory at <a style="color:#fff;text-decoration:underline" '
    'href="https://ubuntu.com/security/CVE-2026-98432">ubuntu.com/security/CVE-2026-98432</a>.'
    "</div>"
)
html = re.sub(r"(<body\b[^>]*>)", lambda m: m.group(1) + "\n" + banner, html, count=1)

# In-page anchors were saved as absolute ubuntu.com URLs; make them local.
html = html.replace('href="https://ubuntu.com/security/CVE-2026-98432#', 'href="#')

scripts = "".join(
    f'<script src="assets/js/{name}" defer></script>\n'
    for name in ("navigation.js", "dynamic-toc.js", "cve-detail.js", "notices.js", "status.js")
)
html += scripts + "</body>\n</html>\n"

(ROOT / "index.html").write_text(html, encoding="utf-8")
print(f"wrote index.html ({len(html):,} bytes)")
