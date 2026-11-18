# ubuntu_sec

Design prototype of proposed changes to three ubuntu.com security pages, aimed at
better transparency and faster notification of candidate fixes (fixes testing in
-proposed or the Ubuntu Pro Edge archive before a security notice is issued).
Not live security data.

Live: https://unco.github.io/ubuntu_sec/

| Page | Based on | Changes |
|---|---|---|
| `index.html` | ubuntu.com/security/CVE-2026-98432 | New Status section (candidate fixes, filters, install steps), shorter Description, Mitigation with expandable how-to. Filters can be set from the URL, e.g. `index.html?q=linux-fips&st=C#status`. |
| `notices.html` | ubuntu.com/security/notices | Candidate fixes tab, critical-CVE alert, candidate fixes RSS feed (`candidates.xml`). |
| `USN-9027-2.html` | ubuntu.com/security/notices/USN-9027-2 | "Fixes still in testing" for the same CVE on other releases, fix timeline, candidate date in the header. |

Tracking, analytics, cookie banner and live chat are removed. Fonts are served
from `assets/fonts`.

## Rebuilding

The original pages are kept in `source/` (the browser-saved CVE page is kept local only; save ubuntu.com/security/CVE-2026-98432 as `source/CVE-2026-98432.html` to rebuild it). The proposed changes live in
`partials/`, `assets/css/` and `assets/js/`. To regenerate the HTML:

    python3 tools/build.py
