# -*- coding: utf-8 -*-
"""GitHub katkı serisi kartını gerçek veriden üretir -> assets/streak.svg

Veri: github.com/users/<kullanıcı>/contributions  (token gerektirmez)
Hesap 1 yılı geçtiğinde de doğru kalsın diye katkılar yıl yıl çekilip birleştirilir.
Yerleşim, streak-stats kartının ölçülen geometrisiyle birebir aynıdır.
"""
import datetime as dt
import html as htmllib
import io
import json
import os
import re
import sys
import urllib.request

USER = os.environ.get("GH_USER", "EmrhnHARPUT")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "streak.svg")

BG = "#08080A"
NUM = "#FFFFFF"
LABEL = "#B9B9BC"
DATES = "#7A7A7E"
RING = "#C70202"
FIRE = "#E11414"
CUR_LABEL = "#E11414"
DIVIDER = "#2E2E33"

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

FIRE_PATH = ("M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 "
             "C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 "
             "C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z "
             "M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 "
             "C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 "
             "C 4.51 16.85 2.36 19 -0.29 19 Z")


def _get(url, accept="text/html"):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (readme-streak-card)", "Accept": accept})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def created_at(user):
    data = json.loads(_get(f"https://api.github.com/users/{user}",
                           "application/vnd.github+json"))
    return dt.date.fromisoformat(data["created_at"][:10])


def fetch_days(user, since):
    """{tarih: katki} — hesabın açıldığı yıldan bugüne, yıl yıl."""
    out = {}
    for year in range(since.year, dt.date.today().year + 1):
        url = (f"https://github.com/users/{user}/contributions"
               f"?from={year}-01-01&to={year}-12-31")
        page = _get(url)
        cells = {}
        for m in re.finditer(r"<td\b([^>]*ContributionCalendar-day[^>]*)>", page):
            a = m.group(1)
            d = re.search(r'data-date="([^"]+)"', a)
            i = re.search(r'id="([^"]+)"', a)
            if d and i:
                cells[i.group(1)] = d.group(1)
        for m in re.finditer(r"<tool-tip[^>]*\bfor=\"([^\"]+)\"[^>]*>(.*?)</tool-tip>",
                             page, re.S):
            cid, txt = m.group(1), htmllib.unescape(m.group(2)).strip()
            if cid not in cells:
                continue
            n = 0 if txt.lower().startswith("no contribution") else \
                int(re.match(r"([\d,]+)", txt).group(1).replace(",", ""))
            out[cells[cid]] = n
    today = dt.date.today()
    days = [(dt.date.fromisoformat(k), v) for k, v in out.items()]
    return sorted(d for d in days if since <= d[0] <= today)


def streaks(days):
    best = run = 0
    b_rng = r_start = None
    for d, n in days:
        if n > 0:
            r_start = r_start or d
            run = (d - r_start).days + 1
            if run > best:
                best, b_rng = run, (r_start, d)
        else:
            r_start, run = None, 0

    cur, c_rng = run, ((r_start, days[-1][0]) if run else None)
    if days and days[-1][1] == 0:
        i, k = len(days) - 2, 0
        while i >= 0 and days[i][1] > 0:
            k += 1
            i -= 1
        cur = k
        c_rng = (days[i + 1][0], days[-2][0]) if k else None
    return cur, best, c_rng, b_rng


def span(rng):
    if not rng:
        return "-"
    a, b = rng
    if a == b:
        return f"{MON[a.month-1]} {a.day}"
    if a.year == b.year:
        return f"{MON[a.month-1]} {a.day} - {MON[b.month-1]} {b.day}"
    return (f"{MON[a.month-1]} {a.day}, {a.year} - "
            f"{MON[b.month-1]} {b.day}, {b.year}")


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(total, cur, best, c_rng, b_rng, since):
    fnt = '"Segoe UI", Ubuntu, sans-serif'
    s = io.StringIO()
    aria = (f"{USER}: toplam {total} katkı, güncel seri {cur} gün, "
            f"en uzun seri {best} gün.")
    s.write("<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink' "
            "style='isolation: isolate' viewBox='0 0 495 195' width='495px' height='195px' "
            f"direction='ltr' role='img' aria-label='{esc(aria)}'>\n")
    s.write("<style>\n"
            "@keyframes currstreak{0%{font-size:3px;opacity:.2}"
            "80%{font-size:34px;opacity:1}100%{font-size:28px;opacity:1}}\n"
            "@keyframes fadein{0%{opacity:0}100%{opacity:1}}\n"
            "@media (prefers-reduced-motion:reduce){*{animation:none!important;opacity:1!important}}\n"
            "</style>\n")
    s.write("<defs><clipPath id='outer_rectangle'><rect width='495' height='195' rx='4.5'/></clipPath>"
            "<mask id='mask_out_ring_behind_fire'><rect width='495' height='195' fill='white'/>"
            "<ellipse cx='247.5' cy='32' rx='13' ry='18' fill='black'/></mask></defs>\n")
    s.write("<g clip-path='url(#outer_rectangle)'>\n")
    s.write(f"  <rect fill='{BG}' rx='4.5' x='0.5' y='0.5' width='494' height='194'/>\n")
    for x in (165, 330):
        s.write(f"  <line x1='{x}' y1='28' x2='{x}' y2='170' vector-effect='non-scaling-stroke' "
                f"stroke-width='1' stroke='{DIVIDER}' stroke-linejoin='miter' "
                "stroke-linecap='square' stroke-miterlimit='3'/>\n")

    def blk(cx, val, label, rng, d1, d2, d3, num_color=NUM, lab_color=LABEL, lab_w=400):
        s.write(f"  <g transform='translate({cx}, 48)'>"
                f"<text x='0' y='32' text-anchor='middle' fill='{num_color}' stroke='none' "
                f"font-family='{fnt}' font-weight='700' font-size='28px' "
                f"style='opacity:0;animation:fadein .5s linear forwards {d1}s'>{val}</text></g>\n")
        s.write(f"  <g transform='translate({cx}, 84)'>"
                f"<text x='0' y='32' text-anchor='middle' fill='{lab_color}' stroke='none' "
                f"font-family='{fnt}' font-weight='{lab_w}' font-size='14px' "
                f"style='opacity:0;animation:fadein .5s linear forwards {d2}s'>{label}</text></g>\n")
        s.write(f"  <g transform='translate({cx}, 114)'>"
                f"<text x='0' y='32' text-anchor='middle' fill='{DATES}' stroke='none' "
                f"font-family='{fnt}' font-weight='400' font-size='12px' "
                f"style='opacity:0;animation:fadein .5s linear forwards {d3}s'>{rng}</text></g>\n")

    blk(82.5, f"{total:,}", "Total Contributions",
        f"{MON[since.month-1]} {since.day}, {since.year} - Present", .6, .7, .8)

    s.write(f"  <g transform='translate(247.5, 108)'>"
            f"<text x='0' y='32' text-anchor='middle' fill='{CUR_LABEL}' stroke='none' "
            f"font-family='{fnt}' font-weight='700' font-size='14px' "
            "style='opacity:0;animation:fadein .5s linear forwards .9s'>Current Streak</text></g>\n")
    s.write(f"  <g transform='translate(247.5, 145)'>"
            f"<text x='0' y='21' text-anchor='middle' fill='{DATES}' stroke='none' "
            f"font-family='{fnt}' font-weight='400' font-size='12px' "
            f"style='opacity:0;animation:fadein .5s linear forwards .9s'>{span(c_rng)}</text></g>\n")
    s.write("  <g mask='url(#mask_out_ring_behind_fire)'>"
            f"<circle cx='247.5' cy='71' r='40' fill='none' stroke='{RING}' stroke-width='5' "
            "style='opacity:0;animation:fadein .5s linear forwards .4s'/></g>\n")
    s.write("  <g transform='translate(247.5, 19.5)' stroke-opacity='0' "
            "style='opacity:0;animation:fadein .5s linear forwards .6s'>"
            "<path d='M -12 -0.5 L 15 -0.5 L 15 23.5 L -12 23.5 L -12 -0.5 Z' fill='none'/>"
            f"<path d='{FIRE_PATH}' fill='{FIRE}' stroke-opacity='0'/></g>\n")
    s.write(f"  <g transform='translate(247.5, 48)'>"
            f"<text x='0' y='32' text-anchor='middle' fill='{NUM}' stroke='none' "
            f"font-family='{fnt}' font-weight='700' font-size='28px' "
            f"style='animation:currstreak .6s linear forwards'>{cur}</text></g>\n")

    blk(412.5, f"{best}", "Longest Streak", span(b_rng), 1.2, 1.3, 1.4)

    s.write("</g>\n</svg>\n")
    return s.getvalue()


def main():
    since = created_at(USER)
    days = fetch_days(USER, since)
    if not days:
        print("HATA: katki verisi alinamadi", file=sys.stderr)
        return 1
    total = sum(n for _, n in days)
    cur, best, c_rng, b_rng = streaks(days)
    svg = build(total, cur, best, c_rng, b_rng, since)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"kullanici    : {USER}  (hesap {since})")
    print(f"gun          : {len(days)}  ({days[0][0]} .. {days[-1][0]})")
    print(f"toplam katki : {total}")
    print(f"guncel seri  : {cur}  ({span(c_rng)})")
    print(f"en uzun seri : {best}  ({span(b_rng)})")
    print(f"yazildi      : {OUT}  ({len(svg):,} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
