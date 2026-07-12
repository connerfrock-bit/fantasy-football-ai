#!/usr/bin/env python3
"""
Yahoo OAuth2 helper (stdlib only). One-time browser authorization, then automatic
token refresh. Credentials + tokens live in pipeline/secrets/ (gitignored).

Usage:
  python pipeline/yahoo_auth.py url          # print the URL to authorize in a browser
  python pipeline/yahoo_auth.py code <CODE>  # exchange the ?code=... from the redirect
  python pipeline/yahoo_auth.py test         # verify access by hitting the Yahoo API

Other modules call access_token() to get a valid (auto-refreshed) bearer token.
"""
import base64, json, os, sys, time, urllib.parse, urllib.request

HERE   = os.path.dirname(os.path.abspath(__file__))
SEC    = os.path.join(HERE, "secrets")
CREDS  = os.path.join(SEC, "yahoo.json")
TOKENS = os.path.join(SEC, "yahoo_tokens.json")
AUTH_URL  = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"

def _creds():
    with open(CREDS, encoding="utf-8") as f:
        return json.load(f)

def _basic(c):
    return "Basic " + base64.b64encode(f'{c["client_id"]}:{c["client_secret"]}'.encode()).decode()

def auth_url():
    c = _creds()
    q = urllib.parse.urlencode({"client_id": c["client_id"], "redirect_uri": c["redirect_uri"],
                                "response_type": "code", "language": "en-us"})
    return f"{AUTH_URL}?{q}"

def _post_token(data):
    c = _creds()
    req = urllib.request.Request(
        TOKEN_URL, data=urllib.parse.urlencode(data).encode(),
        headers={"Authorization": _basic(c), "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def _save_tokens(t):
    t["expires_at"] = time.time() + int(t.get("expires_in", 3600)) - 60   # refresh a minute early
    os.makedirs(SEC, exist_ok=True)
    with open(TOKENS, "w", encoding="utf-8") as f:
        json.dump(t, f)

def exchange(code):
    c = _creds()
    t = _post_token({"grant_type": "authorization_code", "redirect_uri": c["redirect_uri"], "code": code})
    if "access_token" not in t:
        print("FAILED:", t); return
    _save_tokens(t)
    print("OK - tokens saved to", TOKENS)

def access_token():
    """Return a valid bearer token, refreshing with the stored refresh_token if expired."""
    if not os.path.exists(TOKENS):
        raise RuntimeError("No Yahoo tokens yet - run: python pipeline/yahoo_auth.py url")
    with open(TOKENS, encoding="utf-8") as f:
        t = json.load(f)
    if time.time() >= t.get("expires_at", 0):
        c = _creds()
        nt = _post_token({"grant_type": "refresh_token", "redirect_uri": c["redirect_uri"],
                          "refresh_token": t["refresh_token"]})
        nt.setdefault("refresh_token", t["refresh_token"])
        _save_tokens(nt); t = nt
    return t["access_token"]

def test():
    req = urllib.request.Request(
        "https://fantasysports.yahooapis.com/fantasy/v2/game/nfl?format=json",
        headers={"Authorization": "Bearer " + access_token()})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())
    game = d["fantasy_content"]["game"][0]
    print(f"OK - authorized. Current NFL game_key={game.get('game_key')} season={game.get('season')}")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "url":
        print("\n1) Open this URL in your browser and click Agree:\n")
        print("   " + auth_url())
        print("\n2) Your browser redirects to https://localhost/?code=XXXX  (page won't load - that's normal).")
        print("   Copy the code value out of the address bar, then run:\n")
        print("   python pipeline/yahoo_auth.py code <CODE>\n")
    elif cmd == "code" and len(sys.argv) > 2:
        exchange(sys.argv[2])
    elif cmd == "test":
        test()
    else:
        print(__doc__)
