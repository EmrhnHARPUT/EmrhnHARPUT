# -*- coding: utf-8 -*-
"""GitHub katkı verisini çekip assets/contributions.svg üretir.

Veri kaynağı: https://github.com/users/<kullanıcı>/contributions
Bu uç nokta katkı takvimini token'sız HTML olarak döndürür; günlük kesin sayılar
<tool-tip> elemanlarında, hücrelere id üzerinden bağlı.

Hiç harici bağımlılık yok — yalnızca standart kütüphane. GitHub Actions'ta
kurulum gerektirmeden çalışır.
"""
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

# ── palet ────────────────────────────────────────────────────────────────
# Isı haritası SIRALI bir ölçek: tek renk tonu, açıktan koyuya.
# Aşağıdaki 4 adım dataviz doğrulayıcısından geçti (--ordinal, koyu yüzey #0A1220):
#   monoton açıklık · komşu ΔL ≥ 0.06 · sönük uç 2.34:1 · ton yayılımı 30°
RAMP = ["#10557E", "#0B84C8", "#26B9F2", "#7DE9FF"]
EMPTY = "#14202F"          # katkısız gün — rampanın parçası değil
SURFACE_A, SURFACE_B = "#0A1220", "#060C18"
LINE = "#1D3E63"
INK, INK_DIM, INK_FAINT = "#E4F4FF", "#8FA8C4", "#5B7391"
ACCENT = "#4DE3FF"

AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


# ── veri ─────────────────────────────────────────────────────────────────
def fetch(user):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (readme-contrib-card)",
                      "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse(page):
    """(tarih, sayı) listesi döndürür — bugüne kadar, tarihe göre artan."""
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
        if d > today:                      # takvim haftayı tamamlamak için ileri gün basar
            continue
        days.append((d, counts.get(cid, 0)))
    days.sort()
    return days


def streaks(days):
    """(guncel, en_uzun, guncel_aralik, uzun_aralik)"""
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

    # Bugün henüz katkı yoksa seri dünde bitmiş sayılır (GitHub da böyle sayar).
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


def level(n, mx):
    if n <= 0:
        return -1
    if mx <= 1:
        return 3
    q = n / mx
    return 0 if q <= .25 else 1 if q <= .5 else 2 if q <= .75 else 3


# ── çizim ────────────────────────────────────────────────────────────────
W = 1200
PAD = 30
LBL_W = 38                 # gün adı sütunu
CELL, GAP = 16, 4          # marklar arası boşluk — ayırıcı çerçeve DEĞİL
STEP = CELL + GAP


def tr_date(d):
    return f"{d.day} {AY[d.month - 1]} {d.year}"


def build(days):
    total = sum(n for _, n in days)
    mx = max((n for _, n in days), default=0)
    cur, best, cur_rng, best_rng = streaks(days)
    peak = max(days, key=lambda x: x[1]) if days else (None, 0)
    aktif = sum(1 for _, n in days if n > 0)

    # ilk sütun pazar olacak şekilde hizala (GitHub takvimi böyle)
    first = days[0][0]
    lead = (first.weekday() + 1) % 7          # pazar = 0
    weeks = (lead + len(days) + 6) // 7

    gx, gy = PAD + LBL_W, 96
    grid_w = weeks * STEP - GAP
    grid_h = 7 * STEP - GAP

    s = io.StringIO()
    aria = (f"{USER} katkı grafiği: son bir yılda {total} katkı, "
            f"güncel seri {cur} gün, en uzun seri {best} gün.")
    H = gy + grid_h + 128

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
            "</defs>\n")
    s.write(f'<g clip-path="url(#cc)">\n  <rect width="{W}" height="{H}" fill="url(#cbg)"/>\n')

    # başlık
    s.write(f'  <text x="{PAD}" y="44" fill="{INK}" font-size="19" font-weight="600">'
            f'Katkı Grafiği</text>\n')
    s.write(f'  <text x="{PAD}" y="66" fill="{INK_DIM}" font-size="12.5">'
            f'{tr_date(days[0][0])} — {tr_date(days[-1][0])}</text>\n')
    s.write(f'  <text class="m" x="{W-PAD}" y="44" text-anchor="end" fill="{ACCENT}" '
            f'font-size="12">@{USER}</text>\n')

    # ay etiketleri
    seen = set()
    for idx, (d, _n) in enumerate(days):
        col = (lead + idx) // 7
        if d.month not in seen and d.day <= 7:
            seen.add(d.month)
            s.write(f'    <text class="m" x="{gx + col*STEP}" y="{gy - 8}" '
                    f'fill="{INK_FAINT}" font-size="10.5">{AY[d.month-1]}</text>\n')

    # gün adları — üç tanesi yeter, hepsi kalabalık yapar
    for r, nm in ((1, "Pzt"), (3, "Çrş"), (5, "Cum")):
        s.write(f'  <text class="m" x="{PAD}" y="{gy + r*STEP + CELL - 4}" '
                f'fill="{INK_FAINT}" font-size="10.5">{nm}</text>\n')

    # ısı haritası — hücrelerde stroke YOK, ayrım GAP ile
    for idx, (d, n) in enumerate(days):
        p = lead + idx
        col, row = p // 7, p % 7
        lv = level(n, mx)
        fill = EMPTY if lv < 0 else RAMP[lv]
        s.write(f'    <rect x="{gx + col*STEP}" y="{gy + row*STEP}" width="{CELL}" '
                f'height="{CELL}" rx="3" fill="{fill}"/>\n')

    # ölçek göstergesi — sıralı skalada zorunlu
    ly = gy + grid_h + 26
    lx = W - PAD - (5 * (CELL + 4) + 78)
    s.write(f'  <text x="{lx}" y="{ly + CELL - 4}" fill="{INK_FAINT}" font-size="11">Az</text>\n')
    for i, c in enumerate([EMPTY] + RAMP):
        s.write(f'    <rect x="{lx + 24 + i*(CELL+4)}" y="{ly}" width="{CELL}" height="{CELL}" '
                f'rx="3" fill="{c}"/>\n')
    s.write(f'  <text x="{lx + 24 + 5*(CELL+4) + 6}" y="{ly + CELL - 4}" fill="{INK_FAINT}" '
            f'font-size="11">Çok</text>\n')

    # sayı kutuları — değerler metin renginde, seri renginde DEĞİL
    ty = ly + 44
    tiles = [
        (f"{total:,}".replace(",", "."), "katkı (son 1 yıl)"),
        (f"{cur}", "günlük güncel seri"),
        (f"{best}", "günlük en uzun seri"),
        (f"{aktif}", "aktif gün"),
    ]
    tw = (W - 2 * PAD - 3 * 16) / 4
    for i, (val, lab) in enumerate(tiles):
        x = PAD + i * (tw + 16)
        s.write(f'    <rect x="{x:.0f}" y="{ty}" width="{tw:.0f}" height="62" rx="9" '
                f'fill="#0E1A2B" stroke="{LINE}"/>\n')
        s.write(f'    <rect x="{x:.0f}" y="{ty}" width="3" height="62" rx="1.5" fill="{ACCENT}" '
                f'opacity=".8"/>\n')
        s.write(f'    <text x="{x+18:.0f}" y="{ty+30}" fill="{INK}" font-size="22" '
                f'font-weight="700">{val}</text>\n')
        s.write(f'    <text x="{x+18:.0f}" y="{ty+50}" fill="{INK_DIM}" font-size="12">{lab}</text>\n')

    if peak[0]:
        s.write(f'  <text x="{PAD}" y="{ly + CELL - 4}" fill="{INK_FAINT}" font-size="11.5">'
                f'En yoğun gün: {tr_date(peak[0])} — {peak[1]} katkı</text>\n')

    s.write(f'  <rect width="{W}" height="{H}" fill="url(#cscan)"/>\n')
    s.write("</g>\n</svg>\n")

    return s.getvalue(), dict(total=total, cur=cur, best=best, mx=mx,
                              aktif=aktif, peak=peak, gun=len(days))


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
