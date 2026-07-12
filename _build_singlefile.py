# Inlines everything into single self-contained .html files (Gmail-attachable).
import os

SRC = r"C:\Users\conne\Desktop\Fantasy Football Tools"                 # flat offline bundle
OUT = r"C:\Users\conne\Desktop\Fantasy Football Tools (email-ready)"
os.makedirs(OUT, exist_ok=True)

def read(p):
    return open(os.path.join(SRC, p), encoding="utf-8", errors="replace").read()

def esc(js):                      # make JS safe to embed inside <script>...</script>
    return js.replace("</script", "<\\/script")

react       = esc(read("react.production.min.js"))
reactdom    = esc(read("react-dom.production.min.js"))
# When support.js is inlined, the page source contains its literal "<x-dc>"/"</x-dc>"
# parser strings. The runtime's post-render re-fetch (fetch(location.href) -> parse the
# raw source as a string) then grabs the wrong boundaries and overwrites the good DOM
# render with source text. The initial DOM-based render is already complete, so we make
# that one re-fetch a no-op (it falls through to the existing .catch()).
support     = esc(read("support.js").replace("fetch(location.href)", "Promise.reject(0)"))
ffplayers   = esc(read("ff_players.js"))
playersdata = esc(read("players-data.js"))
fonts       = read("fonts.css")   # CSS -> <style> (no </script> concern)

PAGES = [
    ("Draft Cockpit.dc.html",    "Draft Cockpit.html"),
    ("Lineup Optimizer.dc.html", "Lineup Optimizer.html"),
    ("Player Database.dc.html",  "Player Database.html"),
]

for src_name, out_name in PAGES:
    html = read(src_name)
    html = html.replace('<script src="react.production.min.js"></script>',     '<script>' + react + '</script>')
    html = html.replace('<script src="react-dom.production.min.js"></script>', '<script>' + reactdom + '</script>')
    html = html.replace('<script src="./support.js"></script>',               '<script>' + support + '</script>')
    html = html.replace('<script src="ff_players.js"></script>',              '<script>' + ffplayers + '</script>')
    html = html.replace('<script src="players-data.js"></script>',            '<script>' + playersdata + '</script>')
    html = html.replace('<link rel="stylesheet" href="fonts.css">',          '<style>' + fonts + '</style>')
    # cross-page nav: point at the new plain .html filenames
    html = (html.replace('Cockpit.dc.html', 'Cockpit.html')
                .replace('Optimizer.dc.html', 'Optimizer.html')
                .replace('Database.dc.html', 'Database.html'))
    open(os.path.join(OUT, out_name), "w", encoding="utf-8").write(html)
    # report any remaining external refs (should be none)
    leftover = [s for s in ('src="react', 'src="./support', 'src="ff_players', 'src="players-data', 'href="fonts.css', 'pipeline/data', 'unpkg', 'googleapis') if s in html]
    print("%-26s -> %-24s %d KB   leftover-ext: %s" % (src_name, out_name, len(html)//1024, leftover or "none"))

print("\nOUT:", OUT)
