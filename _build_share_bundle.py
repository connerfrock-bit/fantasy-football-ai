# Builds a flat, fully-offline, shareable bundle of the three .dc.html tools.
import os, re, shutil, base64, urllib.request

PROJ   = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.join(PROJ, "Design")
FFPLAY = os.path.join(PROJ, "pipeline", "data", "ff_players.js")
OUT    = r"C:\Users\conne\Desktop\Fantasy Football Tools"

HTML_FILES = ["Draft Cockpit.dc.html", "Lineup Optimizer.dc.html", "Player Database.dc.html"]

os.makedirs(OUT, exist_ok=True)

def dl(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()

manifest = []

# 1) copy same-folder runtime + data
for f in ["support.js", "players-data.js"]:
    shutil.copy2(os.path.join(DESIGN, f), os.path.join(OUT, f))
    manifest.append(f)
shutil.copy2(FFPLAY, os.path.join(OUT, "ff_players.js"))   # flattened from pipeline/data/
manifest.append("ff_players.js")

# 2) download React UMD (global build -> sets window.React / window.ReactDOM)
for fn, url in [("react.production.min.js",     "https://unpkg.com/react@18.3.1/umd/react.production.min.js"),
                ("react-dom.production.min.js", "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js")]:
    with open(os.path.join(OUT, fn), "wb") as fh:
        fh.write(dl(url))
    manifest.append(fn)

# 3) build fonts.css with latin subset inlined as base64 (no network needed at runtime)
css = dl("https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap").decode("utf-8")
faces = re.findall(r'/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{[^}]*\})', css)
chunks, n_fonts = [], 0
for subset, block in faces:
    if subset != "latin":
        continue
    m = re.search(r'url\((https://[^)]+\.woff2)\)', block)
    if not m:
        continue
    b64 = base64.b64encode(dl(m.group(1))).decode()
    block = block.replace(m.group(1), "data:font/woff2;base64," + b64)
    chunks.append("/* latin */\n" + block)
    n_fonts += 1
with open(os.path.join(OUT, "fonts.css"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(chunks))
manifest.append("fonts.css (%d latin faces inlined)" % n_fonts)

# 4) transform the HTML files into the bundle
font_re = re.compile(
    r'[ \t]*<link rel="preconnect" href="https://fonts\.googleapis\.com">\s*'
    r'<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>\s*'
    r'<link href="https://fonts\.googleapis\.com/css2[^"]*" rel="stylesheet">')

for name in HTML_FILES:
    html = open(os.path.join(DESIGN, name), encoding="utf-8").read()
    # a) pre-load React locally so support.js skips the unpkg CDN
    html = html.replace(
        '<script src="./support.js"></script>',
        '<script src="react.production.min.js"></script>\n'
        '<script src="react-dom.production.min.js"></script>\n'
        '<script src="./support.js"></script>')
    # b) flatten the player-data path
    html = html.replace('../pipeline/data/ff_players.js', 'ff_players.js')
    # c) swap Google Fonts links for the local inlined stylesheet
    html, nsub = font_re.subn('  <link rel="stylesheet" href="fonts.css">', html)
    open(os.path.join(OUT, name), "w", encoding="utf-8").write(html)
    manifest.append("%s  (fonts swapped: %d)" % (name, nsub))

print("BUNDLE ->", OUT)
for m in manifest:
    print("  +", m)
