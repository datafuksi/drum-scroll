"""
Build the drum-scroller data from the PDFs one folder up.

    python build.py

Reads  ../*.pdf   (screenshots of notation, one strip per line; timestamps are either
                   PDF text or baked into the picture -> those are typed in TIMES below)
Writes strips/<song>/NN.webp  and  songs.js

Requires:  pip install pymupdf pillow numpy
To add a song: drop the PDF next to the others, add an entry to SONGS (and TIMES if the
timestamps are inside the picture), run this script.
"""
import io, json, os, re, shutil, statistics
import numpy as np, pymupdf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PDFS = os.path.dirname(HERE)
OUT = os.path.join(HERE, "strips")
MAX_W = 1600

# kind: 'text'  -> one image per strip, timestamps are PDF text
#       'boxes' -> full-page screenshots, strips cut out by their border, times typed in TIMES
#       'bars'  -> bar grid (tempo based)
SONGS = [
    dict(id="beggin", title="Beggin'", artist="Maneskin", pdf="Beggin_drum_notation.pdf", yt="AXFlL2wvUVE", kind="text"),
    dict(id="im-yours", title="I'm Yours", artist="Jason Mraz", pdf="Im_Yours_drum_notation.pdf", yt="GwxRudQD1LU", kind="text"),
    dict(id="summer-of-69", title="Summer of '69", artist="Bryan Adams", pdf="Summer_of_69_drum_notation.pdf", yt="guCBgnc1SM8", kind="bars"),
    dict(id="a-thousand-years", title="A Thousand Years", artist="Christina Perri", pdf="a-thousand-years-drum-notation.pdf", yt="3fioJC4HP9o", kind="boxes"),
    dict(id="beautiful-things", title="Beautiful Things", artist="Benson Boone", pdf="beautiful-things-drum-notation.pdf", yt="aPrBy-6ZASY", kind="boxes"),
    dict(id="cant-help-falling-in-love", title="Can't Help Falling in Love", artist="", pdf="cant-help-falling-in-love-drum-notation.pdf", yt="GfleX0KZMEg", kind="boxes"),
    dict(id="die-with-a-smile", title="Die With A Smile", artist="Lady Gaga & Bruno Mars", pdf="die-with-a-smile-drum-notation.pdf", yt="mwv0N7Nr9Dw", kind="boxes"),
    dict(id="shut-up-and-dance", title="Shut Up and Dance", artist="WALK THE MOON", pdf="shut-up-and-dance-drum-notation.pdf", yt="BQBV8ozdQTM", kind="text"),
    dict(id="stay-with-me", title="Stay With Me", artist="Miki Matsubara", pdf="stay-with-me-drum-notation.pdf", yt="W7GBySYeNGQ", kind="text"),
    dict(id="thinking-out-loud", title="Thinking Out Loud", artist="Ed Sheeran", pdf="thinking-out-loud-drum-notation.pdf", yt="BoCrG1pvO9M", kind="text"),
    dict(id="put-your-head-on-my-shoulder", title="Put Your Head On My Shoulder", artist="Paul Anka", pdf="put-your-head-on-my-shoulder-drum-notation.pdf", yt="tJLDzwxN2wY", kind="boxes", boxx=237),
    dict(id="demons", title="Demons", artist="Imagine Dragons", pdf="Demons_drum_notation.pdf", yt="8OEq06Py1Wc", kind="demons"),
    dict(id="gimme-gimme-gimme", title="Gimme! Gimme! Gimme!", artist="ABBA", pdf="gimme-gimme-gimme-drum-notation.pdf", yt="ntD7DVaKPxI", kind="boxes"),
    dict(id="viva-la-vida", title="Viva La Vida", artist="Coldplay", pdf="viva-la-vida-drum-notation.pdf", yt="cZod6H42XIk", kind="boxes"),
    dict(id="yellow", title="Yellow", artist="Coldplay", pdf="yellow-drum-notation.pdf", yt="Ssz69tFTS7Y", kind="boxes"),
]

# Timestamps printed inside the screenshots (read by eye), strip 1..N, "m:ss(.d)".
TIMES = {
    "a-thousand-years": "0:03.9 0:43.9 1:30.6 1:51.3 2:11.6 2:32.4 2:53.3 3:03.7 3:13.9 3:24.5 3:34.5 3:55.3 4:05.8 4:16.5",
    "beautiful-things": "0:31.5 0:34.8 1:09.3 1:22.5 1:26.6 1:34.9 1:42.9 1:46.9 1:54.9 2:03.0 2:07.1 2:14.0 2:21.7 2:29.9 2:37.9",
    "cant-help-falling-in-love": "0:04.4 0:14.8 0:29.0 0:44.3 0:57.7 1:11.8 1:26.0 1:29.9 1:43.5 1:57.8 2:11.8 2:15.1 2:30.8 2:43.2",
    "die-with-a-smile": "0:27.3 0:46.0 1:04.0 1:17.7 1:26.8 1:35.9 1:45.0 1:54.2 2:03.2 2:21.5 2:35.2 2:53.4 3:02.5 3:11.7 3:35.0 3:44.5",
    "put-your-head-on-my-shoulder": "0:05 0:12 0:19 0:32 0:45 0:58 1:11 1:24 1:40 1:54 2:07 2:20 2:36",
    "gimme-gimme-gimme": "0:11 0:32 0:40 0:48 0:53 1:01 1:11 1:19 1:23 1:31 1:39 1:47 1:55 2:01 2:09 2:19 2:27 2:31 2:39 2:47 2:55 3:02 3:06 3:14 3:46 4:30 4:38 4:46",
    "viva-la-vida": "0:10 0:17 0:29 0:38 0:47 0:55 1:04 1:13 1:20 1:27 1:35 1:44 1:51 2:00 2:09 2:17 2:24 2:31 2:38 2:40 2:52 3:02 3:11 3:19 3:29",
    "yellow": "0:08.4 0:11.7 0:22.8 0:33.6 0:44.9 0:55.6 1:06.7 1:19.2 1:29.0 1:40.8 1:51.4 2:02.1 2:13.2 2:24.3 2:35.3 2:46.4 2:52.0 3:03.0 3:13.9 3:25.3 3:36.2 3:47.2 3:58.6",
}

# Summer of '69: tempo based. Start bar of each cell in the PDF (from the printed bar numbers).
S69_BPM = 138
S69_BEATS = 4
S69_START_BARS = [1, 3] + list(range(14, 48)) + [48, 50, 51, 52] + list(range(54, 70)) + [70, 71, 72]
S69_END_BAR = 75  # bar 72 + the 2-bar rest


def ts(s):
    m, r = s.split(":")
    return int(m) * 60 + float(r)


def to_webp(im, path):
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    im.convert("RGB").save(path, "WEBP", quality=82, method=6)
    return im.width, im.height


def page_image(d, i):
    return Image.open(io.BytesIO(d.extract_image(d[i].get_images()[0][0])["image"])).convert("RGB")


def find_boxes(im, x=80):
    """Strip borders: a long vertical grey line at x (80 for most PDFs)."""
    a = np.asarray(im.convert("L")).astype(int)
    col = a[:, x - 2:x + 3].min(1) < 235
    out, s = [], None
    for y, v in enumerate(list(col) + [False]):
        if v and s is None:
            s = y
        if not v and s is not None:
            if y - s > 60:
                out.append((s, y))
            s = None
    return out


def strips_text(d):
    imgs, times = [], []
    for p in d:
        info = p.get_image_info(xrefs=True)
        info.sort(key=lambda k: k["bbox"][1])
        imgs += [Image.open(io.BytesIO(d.extract_image(k["xref"])["image"])).convert("RGB") for k in info]
        times += [ts(m.group(1)) for m in re.finditer(r"^\d+\s+\S+\s+(\d+:\d{2})\s*$", p.get_text(), re.M)]
    assert len(imgs) == len(times), (len(imgs), len(times))
    return imgs, times


def strips_boxes(d, tstr, x=80):
    imgs = []
    for i in range(len(d)):
        im = page_image(d, i)
        a = np.asarray(im.convert("L")).astype(int)
        for (y0, y1) in find_boxes(im, x):
            right = np.where(a[y0 + 2] < 250)[0].max() + 1
            imgs.append(im.crop((x - 2, y0, right, y1)))
    times = [ts(x) for x in tstr.split()]
    assert len(imgs) == len(times), (len(imgs), len(times))
    return imgs, times


def staff_mid(cell):
    a = np.asarray(cell.convert("L")).astype(int)
    w = a.shape[1]
    dark = (a[:, int(w * .12):int(w * .9)] < 130).mean(1) > .8
    ys = np.where(dark)[0]
    if len(ys) < 3:
        return None
    groups, g = [], [ys[0]]
    for y in ys[1:]:
        if y - g[-1] <= 2:
            g.append(y)
        else:
            groups.append(g)
            g = [y]
    groups.append(g)
    c = [np.mean(x) for x in groups]
    return c[2] if len(c) >= 5 else c[len(c) // 2]


def strips_bars(d):
    cells = []
    for i in range(len(d)):
        info = d[i].get_image_info(xrefs=True)
        info.sort(key=lambda k: (round(k["bbox"][1] / 10), k["bbox"][0]))
        cells += [Image.open(io.BytesIO(d.extract_image(k["xref"])["image"])).convert("RGB") for k in info]
    assert len(cells) == len(S69_START_BARS), (len(cells), len(S69_START_BARS))
    bar = S69_BEATS * 60 / S69_BPM
    starts = [(b - 1) * bar for b in S69_START_BARS] + [(S69_END_BAR - 1) * bar]
    rows, times, segs = [], [], []
    for r in range(0, len(cells), 2):
        pair = cells[r:r + 2]
        mids = [staff_mid(c) or c.height * .6 for c in pair]
        top = max(mids)
        bot = max(c.height - m for c, m in zip(pair, mids))
        cw = max(c.width for c in pair)
        gap = 8
        W = cw * len(pair) + gap * (len(pair) - 1)
        H = int(round(top + bot))
        row = Image.new("RGB", (W, H), pair[0].getpixel((3, 3)))
        sg = []
        for k, (c, m) in enumerate(zip(pair, mids)):
            row.paste(c, (k * (cw + gap), int(round(top - m))))
            x0 = (k * (cw + gap) + c.width * .035) / W
            x1 = (k * (cw + gap) + c.width * .985) / W
            sg.append([round(x0, 4), round(x1, 4), round(starts[r + k], 3), round(starts[r + k + 1], 3)])
        rows.append(row)
        times.append(starts[r])
        segs.append(sg)
    return rows, times, segs, starts[-1]


# Demons: 3 video screens of systems, 90 bpm 4/4. The video plays bars 1-24, repeats to bar 1
# (at 1:08), then plays 1-40. Bar 1 = 0:04. Checks: bar 20 = 0:55, 2nd bar 35 = 2:39.
DEM_BPM = 90
DEM_T0 = 4.0
DEM_ROWS = [[1, 8, 12, 16], [20, 23, 27, 31], [35, 38]]   # first bar of each system, per screen
DEM_END = 41


def split_systems(im):
    g = np.asarray(im.convert("L")).astype(int)
    dark = (g[:, 100:im.width - 60] < 120).mean(1) > .6
    ys = list(np.where(dark)[0])
    staffs, cur = [], [ys[0]]
    for y in ys[1:]:
        if y - cur[-1] <= 14: cur.append(y)
        else: staffs.append(cur); cur = [y]
    staffs.append(cur)
    staffs = [(min(s), max(s)) for s in staffs if max(s) - min(s) > 30]
    cuts = [0] + [staffs[i][1] + int((staffs[i + 1][0] - staffs[i][1]) * .42) for i in range(len(staffs) - 1)] + [min(im.height, staffs[-1][1] + 90)]
    return [im.crop((0, cuts[i], im.width, cuts[i + 1])) for i in range(len(staffs))]


def strips_demons(d):
    screens = []
    for p in d:
        for k in sorted(p.get_image_info(xrefs=True), key=lambda k: k["bbox"][1]):
            screens.append(Image.open(io.BytesIO(d.extract_image(k["xref"])["image"])).convert("RGB"))
    rows = {}
    for si, sc in enumerate(screens):
        sy = split_systems(sc)
        assert len(sy) == len(DEM_ROWS[si]), (si, len(sy))
        for b, im in zip(DEM_ROWS[si], sy): rows[b] = im
    bar = 4 * 60 / DEM_BPM
    starts = sorted(rows)
    nxt = {b: (starts[i + 1] if i + 1 < len(starts) else DEM_END) for i, b in enumerate(starts)}
    imgs, times, segs = [], [], []
    # pass 1: bars 1-24, repeat sign sits ~45% across the bar-23 system
    for b in [1, 8, 12, 16, 20, 23]:
        t = DEM_T0 + (b - 1) * bar
        e = DEM_T0 + ((25 if b == 23 else nxt[b]) - 1) * bar
        imgs.append(rows[b]); times.append(t); segs.append([[0.03, 0.45 if b == 23 else 0.99, round(t, 3), round(e, 3)]])
    # pass 2: bars 1-40
    for b in starts:
        t = DEM_T0 + (24 + b - 1) * bar
        e = DEM_T0 + (24 + nxt[b] - 1) * bar
        imgs.append(rows[b]); times.append(t); segs.append([[0.03, 0.99, round(t, 3), round(e, 3)]])
    return imgs, times, segs, DEM_T0 + (24 + DEM_END - 1) * bar


# Visual metronome: (pulse bpm, pulses per bar). Printed tempo where the notation shows one,
# otherwise counted from the strips (12/8 and 6/8 songs pulse in dotted quarters).
# build() snaps each strip gap to whole bars and least-squares fits tempo + downbeat time.
METRO = {
    "beggin": (134, 4), "im-yours": (74, 4), "shut-up-and-dance": (128, 4), "stay-with-me": (108, 4),
    "thinking-out-loud": (79, 4), "die-with-a-smile": (79, 4), "put-your-head-on-my-shoulder": (76, 4),
    "gimme-gimme-gimme": (118, 4), "viva-la-vida": (138, 4), "yellow": (87.5, 4),
    "a-thousand-years": (46.2, 4), "beautiful-things": (70, 2), "cant-help-falling-in-love": (68, 4),
}


def fit_metro(sid, times):
    if sid == "summer-of-69": return dict(bpm=S69_BPM, bpb=S69_BEATS, t0=0.0)
    if sid == "demons": return dict(bpm=DEM_BPM, bpb=4, t0=DEM_T0)
    if sid not in METRO: return None
    bpm, bpb = METRO[sid]
    t = np.array(times); bar = bpb * 60 / bpm
    n = np.round(np.diff(t) / bar); N = np.concatenate([[0], np.cumsum(n)])
    (a0, bl), *_ = np.linalg.lstsq(np.vstack([np.ones_like(N), N]).T, t, rcond=None)
    return dict(bpm=round(bpb * 60 / bl, 2), bpb=bpb, t0=round(float(a0), 3))


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    songs = []
    for s in SONGS:
        d = pymupdf.open(os.path.join(PDFS, s["pdf"]))
        segs = None
        end = None
        if s["kind"] == "text":
            imgs, times = strips_text(d)
        elif s["kind"] == "boxes":
            imgs, times = strips_boxes(d, TIMES[s["id"]], s.get("boxx", 80))
        elif s["kind"] == "demons":
            imgs, times, segs, end = strips_demons(d)
        else:
            imgs, times, segs, end = strips_bars(d)
        if end is None:
            gaps = [b - a for a, b in zip(times, times[1:])]
            end = times[-1] + statistics.median(gaps)  # last strip: estimated
        os.makedirs(os.path.join(OUT, s["id"]), exist_ok=True)
        strips = []
        for i, (im, t) in enumerate(zip(imgs, times)):
            rel = f"strips/{s['id']}/{i + 1:02d}.webp"
            w, h = to_webp(im, os.path.join(HERE, rel))
            st = dict(src=rel, w=w, h=h, t=round(t, 2))
            if segs:
                st["segs"] = segs[i]
            strips.append(st)
        song = dict(id=s["id"], title=s["title"], artist=s["artist"], yt=s["yt"], end=round(end, 2), strips=strips)
        m = fit_metro(s["id"], times)
        if m: song["metro"] = m
        if s["kind"] == "bars":
            song["note"] = f"Tempo based ({S69_BPM} bpm). Press play, then nudge Sync until the drums-in bar (14) lines up."
        songs.append(song)
        print(f"{s['title']:30s} {len(strips):3d} strips  {times[0]:7.1f}s -> {end:7.1f}s")
    with open(os.path.join(HERE, "songs.js"), "w", encoding="utf-8") as f:
        f.write("window.SONGS = " + json.dumps(songs, ensure_ascii=False, separators=(",", ":")) + ";\n")


if __name__ == "__main__":
    main()
