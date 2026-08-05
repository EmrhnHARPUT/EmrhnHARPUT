# -*- coding: utf-8 -*-
"""GitHub katkı verisini çekip assets/contributions.svg üretir."""
import datetime as dt
import html as htmllib
import io
import os
import re
import sys
import urllib.request

USER = os.environ.get("GH_USER", "EmrhnHARPUT")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "contributions.svg")

RAMP = ["#10557E", "#0B84C8", "#26B9F2", "#7DE9FF"]
EMPTY = "#14202F"
GLOW = "#CFF7FF"
SURFACE_A, SURFACE_B = "#0A1220", "#060C18"
LINE = "#1D3E63"
INK, INK_DIM, INK_FAINT = "#E4F4FF", "#8FA8C4", "#5B7391"
ACCENT = "#4DE3FF"

GLOW_EMPTY = 0.05
GLOW_TOP = 0.96
GLOW_MARGIN = 0.96
NEON = "#3FE0FF"

POP = [1.16, 1.26, 1.36, 1.48]
BLOOM = [0.26, 0.42, 0.58, 0.72]
HALO = [0.10, 0.17, 0.24, 0.31]

AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def fetch(user):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (readme-contrib-card)",
                      "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse(page):
    by_id = {}
    for m in re.finditer(r"<td\b([^>]*ContributionCalendar-day[^>]*)>", page):
        a = m.group(1)
        d = re.search(r'data-date="([^"]+)"', a)
        i = re.search(r'id="([^"]+)"', a)
        if d and i:
            by_id[i.group(1)] = d.group(1)

    counts = {}
    for m in re.finditer(r"<tool-tip[^>]*\bfor=\"([^\"]+)\"[^>]*>(.*?)</tool-tip>",
                         page, re.S):
        cid, txt = m.group(1), htmllib.unescape(m.group(2)).strip()
        if cid not in by_id:
            continue
        if txt.lower().startswith("no contribution"):
            counts[cid] = 0
        else:
            num = re.match(r"([\d,]+)", txt)
            counts[cid] = int(num.group(1).replace(",", "")) if num else 0

    today = dt.date.today()
    days = []
    for cid, date_s in by_id.items():
        d = dt.date.fromisoformat(date_s)
        if d > today:
            continue
        days.append((d, counts.get(cid, 0)))
    days.sort()
    return days


def streaks(days):
    best = cur = 0
    best_rng = cur_rng = None
    run_start = None
    for d, n in days:
        if n > 0:
            run_start = run_start or d
            cur = (d - run_start).days + 1
            cur_rng = (run_start, d)
            if cur > best:
                best, best_rng = cur, cur_rng
        else:
            run_start, cur, cur_rng = None, 0, None

    if days and days[-1][1] == 0:
        if len(days) >= 2 and days[-2][1] > 0:
            k, i = 0, len(days) - 2
            while i >= 0 and days[i][1] > 0:
                k += 1
                i -= 1
            cur, cur_rng = k, (days[i + 1][0], days[-2][0])
        else:
            cur, cur_rng = 0, None
    return cur, best, cur_rng, best_rng


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _lum(rgb):
    f = [v / 255 for v in rgb]
    f = [x / 12.92 if x <= .04045 else ((x + .055) / 1.055) ** 2.4 for x in f]
    return .2126 * f[0] + .7152 * f[1] + .0722 * f[2]


def _mix_hex(a, b, t):
    A, B = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(round(A[k] + (B[k] - A[k]) * t) for k in range(3))


def glow_alphas():
    """Her seviye için en yüksek parlama alfası — bir üst seviyenin dinlenme
    parlaklığını asla geçmeyecek şekilde ikili aramayla türetilir."""
    base = _rgb(GLOW)
    rest = [_lum(_rgb(c)) for c in RAMP]
    out = []
    for i, c in enumerate(RAMP):
        if i == len(RAMP) - 1:
            out.append(GLOW_TOP)
            break
        src, cap = _rgb(c), rest[i + 1] * GLOW_MARGIN
        lo, hi = 0.0, 1.0
        for _ in range(48):
            mid = (lo + hi) / 2
            mixed = tuple(src[k] + (base[k] - src[k]) * mid for k in range(3))
            if _lum(mixed) < cap:
                lo = mid
            else:
                hi = mid
        out.append(round(lo, 3))
    return out


def wave_css():
    """Seviye başına bir keyframe: ışık gelince kutucuk hem büyür hem parlar.
    Büyüme oranı da katkıya orantılı, böylece boyut veriyi ikinci kez kodlar."""
    a = glow_alphas()
    hot = [_mix_hex(RAMP[i], GLOW, a[i]) for i in range(len(RAMP))]
    css = ["    .c0,.c1,.c2,.c3{transform-box:fill-box;transform-origin:center}"]
    for i in range(len(RAMP)):
        css.append(
            f"    @keyframes w{i}{{0%,100%{{transform:scale(1);fill:{RAMP[i]}}}"
            f"7%{{transform:scale({POP[i]});fill:{hot[i]}}}"
            f"22%{{transform:scale(1);fill:{RAMP[i]}}}}}")
        css.append(f"    .c{i}{{animation:w{i} {SWEEP}s ease-in-out infinite}}")
        css.append(
            f"    @keyframes b{i}{{0%,100%{{opacity:0;transform:scale(1)}}"
            f"7%{{opacity:{BLOOM[i]};transform:scale({POP[i]+0.25:.2f})}}"
            f"24%{{opacity:0;transform:scale(1)}}}}")
        css.append(f"    .g{i}{{transform-box:fill-box;transform-origin:center;"
                   f"animation:b{i} {SWEEP}s ease-in-out infinite}}")
        css.append(
            f"    @keyframes h{i}{{0%,100%{{opacity:0;transform:scale(1)}}"
            f"7%{{opacity:{HALO[i]};transform:scale({POP[i]+0.42:.2f})}}"
            f"26%{{opacity:0;transform:scale(1)}}}}")
        css.append(f"    .n{i}{{transform-box:fill-box;transform-origin:center;"
                   f"animation:h{i} {SWEEP}s ease-in-out infinite}}")
    css.append(f"    @keyframes we{{0%,100%{{fill:{EMPTY}}}"
               f"7%{{fill:{_mix_hex(EMPTY, GLOW, GLOW_EMPTY)}}}"
               f"22%{{fill:{EMPTY}}}}}")
    css.append(f"    .ce{{animation:we {SWEEP}s ease-in-out infinite}}")
    css.append("    @media (prefers-reduced-motion:reduce){"
               ".c0,.c1,.c2,.c3,.ce,.g0,.g1,.g2,.g3,.n0,.n1,.n2,.n3{animation:none}"
               ".g0,.g1,.g2,.g3,.n0,.n1,.n2,.n3{opacity:0}}")
    return "\n".join(css), hot


def level(n, mx):
    if n <= 0:
        return -1
    if mx <= 1:
        return 3
    q = n / mx
    return 0 if q <= .25 else 1 if q <= .5 else 2 if q <= .75 else 3


W = 1200
PAD = 30
LBL_W = 38
CELL, GAP = 16, 4
STEP = CELL + GAP
SWEEP = 8.5


def tr_date(d):
    return f"{d.day} {AY[d.month - 1]} {d.year}"


def build(days):
    total = sum(n for _, n in days)
    mx = max((n for _, n in days), default=0)
    cur, best, cur_rng, best_rng = streaks(days)
    peak = max(days, key=lambda x: x[1]) if days else (None, 0)
    aktif = sum(1 for _, n in days if n > 0)

    first = days[0][0]
    lead = (first.weekday() + 1) % 7
    weeks = (lead + len(days) + 6) // 7

    gx, gy = PAD + LBL_W, 96
    grid_w = weeks * STEP - GAP
    grid_h = 7 * STEP - GAP

    s = io.StringIO()
    aria = (f"{USER} katkı grafiği: son bir yılda {total} katkı, "
            f"güncel seri {cur} gün, en uzun seri {best} gün.")
    H = gy + grid_h + 66

    s.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}" role="img" aria-label="{aria}">\n')
    s.write('<style>text{font-family:"Segoe UI",Roboto,Ubuntu,Arial,sans-serif}\n'
            '.m{font-family:"Consolas","SF Mono",Menlo,monospace}</style>\n')
    s.write("<defs>\n"
            f'  <clipPath id="cc"><rect width="{W}" height="{H}" rx="14"/></clipPath>\n'
            f'  <linearGradient id="cbg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{H}">'
            f'<stop offset="0" stop-color="{SURFACE_A}"/>'
            f'<stop offset="1" stop-color="{SURFACE_B}"/></linearGradient>\n'
            '  <pattern id="cscan" width="2" height="3" patternUnits="userSpaceOnUse">'
            '<rect width="2" height="1" fill="#000" opacity=".14"/></pattern>\n'
            '  <filter id="cneon" x="-160%" y="-160%" width="420%" height="420%">'
            '<feGaussianBlur stdDeviation="4"/></filter>\n'
            '  <filter id="cneon2" x="-220%" y="-220%" width="540%" height="540%">'
            '<feGaussianBlur stdDeviation="6.5"/></filter>\n'
            "  <style>\n" + wave_css()[0] + "\n  </style>\n"
            "</defs>\n")
    s.write(f'<g clip-path="url(#cc)">\n  <rect width="{W}" height="{H}" fill="url(#cbg)"/>\n')

    s.write(f'  <text x="{PAD}" y="44" fill="{INK}" font-size="19" font-weight="600">'
            f'Katkı Grafiği</text>\n')
    s.write(f'  <text x="{PAD}" y="66" fill="{INK_DIM}" font-size="12.5">'
            f'{tr_date(days[0][0])} — {tr_date(days[-1][0])}</text>\n')
    s.write(f'  <text class="m" x="{W-PAD}" y="44" text-anchor="end" fill="{ACCENT}" '
            f'font-size="12">@{USER}</text>\n')

    seen = set()
    for idx, (d, _n) in enumerate(days):
        col = (lead + idx) // 7
        if d.month not in seen and d.day <= 7:
            seen.add(d.month)
            s.write(f'    <text class="m" x="{gx + col*STEP}" y="{gy - 8}" '
                    f'fill="{INK_FAINT}" font-size="10.5">{AY[d.month-1]}</text>\n')

    for r, nm in ((1, "Pzt"), (3, "Çrş"), (5, "Cum")):
        s.write(f'  <text class="m" x="{PAD}" y="{gy + r*STEP + CELL - 4}" '
                f'fill="{INK_FAINT}" font-size="10.5">{nm}</text>\n')

    hot = wave_css()[1]
    cells = []
    for idx, (d, n) in enumerate(days):
        p = lead + idx
        col, row = p // 7, p % 7
        cells.append((gx + col * STEP, gy + row * STEP, level(n, mx),
                      SWEEP * col / max(weeks, 1)))

    for cx, cy, lv, dly in cells:
        if lv < 0:
            continue
        s.write(f'    <rect class="n{lv}" x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" '
                f'rx="5" fill="{NEON}" opacity="0" filter="url(#cneon2)" '
                f'style="animation-delay:{dly:.3f}s"/>\n')
    for cx, cy, lv, dly in cells:
        if lv < 0:
            continue
        s.write(f'    <rect class="g{lv}" x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" '
                f'rx="4" fill="{NEON}" opacity="0" filter="url(#cneon)" '
                f'style="animation-delay:{dly:.3f}s"/>\n')

    for cx, cy, lv, dly in cells:
        cls = "ce" if lv < 0 else f"c{lv}"
        fill = EMPTY if lv < 0 else RAMP[lv]
        s.write(f'    <rect class="{cls}" x="{cx}" y="{cy}" width="{CELL}" height="{CELL}" '
                f'rx="3" fill="{fill}" style="animation-delay:{dly:.3f}s"/>\n')

    ly = gy + grid_h + 26
    lx = W - PAD - (5 * (CELL + 4) + 78)
    s.write(f'  <text x="{lx}" y="{ly + CELL - 4}" fill="{INK_FAINT}" font-size="11">Az</text>\n')
    for i, c in enumerate([EMPTY] + RAMP):
        s.write(f'    <rect x="{lx + 24 + i*(CELL+4)}" y="{ly}" width="{CELL}" height="{CELL}" '
                f'rx="3" fill="{c}"/>\n')
    s.write(f'  <text x="{lx + 24 + 5*(CELL+4) + 6}" y="{ly + CELL - 4}" fill="{INK_FAINT}" '
            f'font-size="11">Çok</text>\n')

    s.write(f'  <rect width="{W}" height="{H}" fill="url(#cscan)"/>\n')
    s.write("</g>\n</svg>\n")

    return s.getvalue(), dict(total=total, cur=cur, best=best, mx=mx,
                              aktif=aktif, peak=peak, gun=len(days))


def build_activity(days, n=30):
    d = days[-n:]
    mx = max((v for _, v in d), default=0)
    ymax = max(4, -(-mx // 4) * 4)
    total = sum(v for _, v in d)

    W2, H2 = 1200, 352
    px0, px1 = PAD + 52, W2 - PAD
    py0, py1 = 116, 296
    pw, ph = px1 - px0, py1 - py0
    step = pw / max(len(d) - 1, 1)

    pts = [(px0 + i * step, py1 - (v / ymax) * ph) for i, (_dt, v) in enumerate(d)]

    def spline(p):
        out = [f"M{p[0][0]:.1f},{p[0][1]:.1f}"]
        for i in range(len(p) - 1):
            p0, p1 = p[max(i - 1, 0)], p[i]
            p2, p3 = p[i + 1], p[min(i + 2, len(p) - 1)]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            c1 = (c1[0], min(max(c1[1], py0), py1))
            c2 = (c2[0], min(max(c2[1], py0), py1))
            out.append(f"C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} "
                       f"{p2[0]:.1f},{p2[1]:.1f}")
        return " ".join(out)

    line = spline(pts)
    area = line + f" L{pts[-1][0]:.1f},{py1} L{pts[0][0]:.1f},{py1} Z"
    hi = max(range(len(d)), key=lambda i: d[i][1])

    s = io.StringIO()
    aria = (f"{USER} son {len(d)} günlük aktivite: toplam {total} katkı, "
            f"en yüksek gün {d[hi][1]}.")
    s.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W2} {H2}" '
            f'width="{W2}" height="{H2}" role="img" aria-label="{aria}">\n')
    s.write('<style>text{font-family:"Segoe UI",Roboto,Ubuntu,Arial,sans-serif}\n'
            '.m{font-family:"Consolas","SF Mono",Menlo,monospace}\n'
            '@keyframes ap{0%,100%{opacity:.35;r:5}50%{opacity:1;r:9}}\n'
            '.ap{animation:ap 2.6s ease-in-out infinite}\n'
            '@media (prefers-reduced-motion:reduce){.ap{animation:none}}</style>\n')
    s.write("<defs>\n"
            f'  <clipPath id="ac"><rect width="{W2}" height="{H2}" rx="14"/></clipPath>\n'
            f'  <linearGradient id="abg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{H2}">'
            f'<stop offset="0" stop-color="{SURFACE_A}"/>'
            f'<stop offset="1" stop-color="{SURFACE_B}"/></linearGradient>\n'
            f'  <linearGradient id="aar" gradientUnits="userSpaceOnUse" x1="0" y1="{py0}" x2="0" y2="{py1}">'
            f'<stop offset="0" stop-color="{ACCENT}" stop-opacity=".50"/>'
            f'<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>\n'
            '  <filter id="aglow" x="-30%" y="-80%" width="160%" height="300%">'
            '<feGaussianBlur stdDeviation="3.5"/></filter>\n'
            '  <pattern id="ascan" width="2" height="3" patternUnits="userSpaceOnUse">'
            '<rect width="2" height="1" fill="#000" opacity=".14"/></pattern>\n'
            "</defs>\n")
    s.write(f'<g clip-path="url(#ac)">\n  <rect width="{W2}" height="{H2}" fill="url(#abg)"/>\n')
    s.write(f'  <text x="{PAD}" y="46" fill="{INK}" font-size="22" font-weight="600">Aktivite</text>\n')
    s.write(f'  <text x="{PAD}" y="72" fill="{INK_DIM}" font-size="14">'
            f'Son {len(d)} gün — {tr_date(d[0][0])} / {tr_date(d[-1][0])} · '
            f'toplam {total} katkı · günlük ort. {total/max(len(d),1):.1f} · '
            f'en yüksek {d[hi][1]}</text>\n')

    for i, (dt_, _v) in enumerate(d):
        if dt_.weekday() >= 5:
            s.write(f'  <rect x="{pts[i][0]-step/2:.1f}" y="{py0}" width="{step:.1f}" '
                    f'height="{ph}" fill="{ACCENT}" opacity=".055"/>\n')

    xticks = list(range(0, len(d), 6))
    for i in range(len(d)):
        op = ".40" if i in xticks else ".18"
        s.write(f'  <line x1="{pts[i][0]:.1f}" y1="{py0}" x2="{pts[i][0]:.1f}" y2="{py1}" '
                f'stroke="{LINE}" stroke-width="1" opacity="{op}"/>\n')

    for k in range(5):
        v = ymax * k / 4
        y = py1 - (v / ymax) * ph
        s.write(f'  <line x1="{px0}" y1="{y:.1f}" x2="{px1}" y2="{y:.1f}" stroke="{LINE}" '
                f'stroke-width="1" opacity="{"1" if k == 0 else ".55"}"/>\n')
        s.write(f'  <text class="m" x="{px0-14}" y="{y+4:.1f}" text-anchor="end" '
                f'fill="{INK_FAINT}" font-size="13">{int(v)}</text>\n')

    s.write(f'  <path d="{area}" fill="url(#aar)"/>\n')

    ort = total / max(len(d), 1)
    oy = py1 - (ort / ymax) * ph
    s.write(f'  <line x1="{px0}" y1="{oy:.1f}" x2="{px1}" y2="{oy:.1f}" stroke="{INK_DIM}" '
            f'stroke-width="1" stroke-dasharray="6 5" opacity=".75"/>\n')
    s.write(f'  <text class="m" x="{px1-4}" y="{oy-7:.1f}" text-anchor="end" '
            f'fill="{INK_DIM}" font-size="12" opacity=".9">ort.</text>\n')

    s.write(f'  <path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="7" '
            f'opacity=".32" filter="url(#aglow)" stroke-linejoin="round" stroke-linecap="round"/>\n')
    s.write(f'  <path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="3.2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>\n')

    for i, (x, y) in enumerate(pts[:-1]):
        v = d[i][1]
        if v == 0:
            s.write(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{SURFACE_A}" '
                    f'stroke="{LINE}" stroke-width="1.8"/>\n')
        else:
            r = 3.0 + 1.9 * (v / max(mx, 1))
            s.write(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{SURFACE_A}" '
                    f'stroke="{ACCENT}" stroke-width="2.1"/>\n')

    for i in xticks:
        s.write(f'    <text class="m" x="{pts[i][0]:.1f}" y="{py1+28}" text-anchor="middle" '
                f'fill="{INK_FAINT}" font-size="13">{d[i][0].day} {AY[d[i][0].month-1]}</text>\n')

    lx, ly2 = pts[-1]
    s.write(f'  <circle class="ap" cx="{lx:.1f}" cy="{ly2:.1f}" r="5" fill="{ACCENT}" '
            f'filter="url(#aglow)"/>\n')
    s.write(f'  <circle cx="{lx:.1f}" cy="{ly2:.1f}" r="3.4" fill="{INK}"/>\n')

    s.write(f'  <rect width="{W2}" height="{H2}" fill="url(#ascan)"/>\n')
    s.write("</g>\n</svg>\n")
    return s.getvalue()


def main():
    page = fetch(USER)
    days = parse(page)
    if not days:
        print("HATA: katki verisi ayristirilamadi", file=sys.stderr)
        return 1
    svg, st = build(days)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    act = build_activity(days)
    with io.open(os.path.join(os.path.dirname(OUT), "activity.svg"), "w", encoding="utf-8") as f:
        f.write(act)
    print(f"aktivite      : assets/activity.svg  ({len(act):,} bayt)")
    print(f"kullanici     : {USER}")
    print(f"gun sayisi    : {st['gun']}  ({days[0][0]} .. {days[-1][0]})")
    print(f"toplam katki  : {st['total']}")
    print(f"guncel seri   : {st['cur']} gun")
    print(f"en uzun seri  : {st['best']} gun")
    print(f"aktif gun     : {st['aktif']}")
    print(f"en yogun gun  : {st['peak'][0]} ({st['peak'][1]} katki)")
    print(f"yazildi       : {OUT}  ({len(svg):,} bayt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
