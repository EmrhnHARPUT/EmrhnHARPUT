import io

BG = "#08080A"
TQ, TQ_HI = "#2BB3BA", "#45D6DD"
GRID, INK, INK_DIM = "#23262B", "#E8EAED", "#9AA0A6"

AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
      "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

W, H = 1600, 470
PAD = 40
PX0, PX1 = PAD + 62, W - PAD
PY0, PY1 = 150, 390

FNT = '"Segoe UI", Ubuntu, Roboto, sans-serif'
MONO = '"Consolas", "SF Mono", Menlo, monospace'


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _spline(p, ylo, yhi):
    """Catmull-Rom -> kübik bezier. Kontrol noktaları çizim alanına sıkıştırılır,
    yoksa eğri sıfır çizgisinin altına taşıp olmayan negatif katkı gösterir."""
    out = ["M%.1f,%.1f" % (p[0][0], p[0][1])]
    for i in range(len(p) - 1):
        p0, p1 = p[max(i - 1, 0)], p[i]
        p2, p3 = p[i + 1], p[min(i + 2, len(p) - 1)]
        c1y = min(max(p1[1] + (p2[1] - p0[1]) / 6, ylo), yhi)
        c2y = min(max(p2[1] - (p3[1] - p1[1]) / 6, ylo), yhi)
        out.append("C%.1f,%.1f %.1f,%.1f %.1f,%.1f" % (
            p1[0] + (p2[0] - p0[0]) / 6, c1y,
            p2[0] - (p3[0] - p1[0]) / 6, c2y,
            p2[0], p2[1]))
    return " ".join(out)


def build(days, user, n=30):
    d = days[-n:]
    if not d:
        return None

    mx = max(v for _, v in d)
    ymax = max(4, -(-mx // 4) * 4)
    total = sum(v for _, v in d)
    ort = total / len(d)
    hi = max(range(len(d)), key=lambda i: d[i][1])

    pw, ph = PX1 - PX0, PY1 - PY0
    step = pw / max(len(d) - 1, 1)
    pts = [(PX0 + i * step, PY1 - (v / ymax) * ph) for i, (_dt, v) in enumerate(d)]
    line = _spline(pts, PY0, PY1)
    area = line + " L%.1f,%d L%.1f,%d Z" % (pts[-1][0], PY1, pts[0][0], PY1)
    xticks = list(range(0, len(d), 6))

    aria = ("%s son %d günlük aktivite: toplam %d katkı, günlük ortalama %.1f, "
            "en yüksek %d." % (user, len(d), total, ort, d[hi][1]))

    s = io.StringIO()
    s.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" '
            'height="%d" role="img" aria-label="%s">' % (W, H, W, H, _esc(aria)))
    s.write('<style>text{font-family:%s}.m{font-family:%s}'
            '@keyframes ap{0%%,100%%{opacity:.35}50%%{opacity:1}}'
            '.ap{animation:ap 2.6s ease-in-out infinite}'
            '@media (prefers-reduced-motion:reduce){.ap{animation:none}}</style>' % (FNT, MONO))
    s.write('<defs><clipPath id="ac"><rect width="%d" height="%d" rx="14"/></clipPath>'
            '<linearGradient id="aar" gradientUnits="userSpaceOnUse" x1="0" y1="%d" x2="0" y2="%d">'
            '<stop offset="0" stop-color="%s" stop-opacity=".50"/>'
            '<stop offset="1" stop-color="%s" stop-opacity="0"/></linearGradient>'
            '<filter id="agl" x="-30%%" y="-80%%" width="160%%" height="300%%">'
            '<feGaussianBlur stdDeviation="4"/></filter></defs>' % (W, H, PY0, PY1, TQ, TQ))
    s.write('<g clip-path="url(#ac)"><rect width="%d" height="%d" fill="%s"/>' % (W, H, BG))

    s.write('<text x="%d" y="56" fill="%s" font-size="26" font-weight="600">Aktivite</text>'
            % (PAD, INK))
    s.write('<text x="%d" y="88" fill="%s" font-size="16">Son %d gün · %d %s – %d %s %d · '
            'toplam %d katkı · günlük ort. %.1f · en yüksek %d</text>'
            % (PAD, INK_DIM, len(d), d[0][0].day, AY[d[0][0].month - 1],
               d[-1][0].day, AY[d[-1][0].month - 1], d[-1][0].year, total, ort, d[hi][1]))

    for i, (dt_, _v) in enumerate(d):
        if dt_.weekday() >= 5:
            s.write('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s" opacity=".05"/>'
                    % (pts[i][0] - step / 2, PY0, step, ph, TQ))

    for i in range(len(d)):
        s.write('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s" stroke-width="1" '
                'opacity="%s"/>' % (pts[i][0], PY0, pts[i][0], PY1, GRID,
                                    ".42" if i in xticks else ".18"))

    for k in range(5):
        v = ymax * k / 4
        y = PY1 - (v / ymax) * ph
        s.write('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1" '
                'opacity="%s"/>' % (PX0, y, PX1, y, GRID, "1" if k == 0 else ".6"))
        s.write('<text class="m" x="%d" y="%.1f" text-anchor="end" fill="%s" '
                'font-size="15">%d</text>' % (PX0 - 16, y + 5, INK_DIM, int(v)))

    s.write('<path d="%s" fill="url(#aar)"/>' % area)

    oy = PY1 - (ort / ymax) * ph
    s.write('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.2" '
            'stroke-dasharray="7 6" opacity=".7"/>' % (PX0, oy, PX1, oy, INK_DIM))
    s.write('<text class="m" x="%d" y="%.1f" text-anchor="end" fill="%s" font-size="14" '
            'opacity=".9">ort.</text>' % (PX1 - 6, oy - 10, INK_DIM))

    s.write('<path d="%s" fill="none" stroke="%s" stroke-width="7" opacity=".30" '
            'filter="url(#agl)" stroke-linejoin="round" stroke-linecap="round"/>' % (line, TQ))
    s.write('<path d="%s" fill="none" stroke="%s" stroke-width="3.2" '
            'stroke-linejoin="round" stroke-linecap="round"/>' % (line, TQ_HI))

    for i, (x, y) in enumerate(pts[:-1]):
        v = d[i][1]
        if v == 0:
            s.write('<circle cx="%.1f" cy="%.1f" r="2.6" fill="%s" stroke="%s" '
                    'stroke-width="1.8"/>' % (x, y, BG, GRID))
        else:
            s.write('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" '
                    'stroke-width="2.1"/>' % (x, y, 3.0 + 1.9 * (v / max(mx, 1)), BG, TQ_HI))

    for i in xticks:
        s.write('<text class="m" x="%.1f" y="%d" text-anchor="middle" fill="%s" '
                'font-size="15">%d %s</text>'
                % (pts[i][0], PY1 + 30, INK_DIM, d[i][0].day, AY[d[i][0].month - 1]))

    lx, ly = pts[-1]
    s.write('<circle class="ap" cx="%.1f" cy="%.1f" r="6" fill="%s" filter="url(#agl)"/>'
            % (lx, ly, TQ_HI))
    s.write('<circle cx="%.1f" cy="%.1f" r="3.6" fill="%s"/>' % (lx, ly, INK))
    s.write("</g></svg>")
    return s.getvalue()
