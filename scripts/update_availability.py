"""
Fetch the Dining Week restaurant list and write availability.json for the map.

Runs every hour on GitHub Actions (see .github/workflows/update.yml).
Can also be run by hand:  python scripts/update_availability.py [output.json]

The output format matches what the map's in-browser parser produces:
  {"ts": <epoch ms>, "source": "...", "agg": {res_id: {n, c, u, m, days, slots, L, D, allSold}}}
  slots = [[day, party_size, "L" | "D"], ...]  (L = lunch/frokost, D = dinner/aften)
"""

import json
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

URL = "https://diningweek.dk/restaurants"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/128.0 Safari/537.36 (personal Dining Week map; hourly)"),
    "Accept-Language": "da-DK,da;q=0.9,en;q=0.8",
}
MENU_CLASS = {"3retter": "3 retter", "5serveringer": "5 serveringer",
              "tasting": "Tasting", "en_bid": "En bid af stjernerne"}
DATE_RE = re.compile(r"^date\d{4}-\d{2}-(\d{2})$")
SLOT_RE = re.compile(r"^date\d{4}-\d{2}-(\d{2})pax(\d+)(frokost|aften)$")
PRICE_RE = re.compile(r"(\d{3,4})\s*kr")


def fetch(retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(URL, headers=HEADERS, timeout=60)
            if r.ok and "res_grid_item_" in r.text:
                return r.text
            last = f"HTTP {r.status_code}"
        except Exception as e:
            last = str(e)
        time.sleep(10 * (i + 1))
    sys.exit(f"Could not fetch {URL}: {last}")


def text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip() if el else ""


def parse(html):
    soup = BeautifulSoup(html, "html.parser")
    agg = {}
    for card in soup.select("div.grid-item[data-res_id]"):
        rid = (card.get("data-res_id") or "").strip()
        if not rid:
            continue
        cls = card.get("class", [])
        a = agg.get(rid)
        if a is None:
            a = agg[rid] = {
                "n": text(card.select_one(".dw-card-name")) or (card.get("data-restaurant") or "").strip(),
                "c": text(card.select_one(".dw-card-city")),
                "u": "https://diningweek.dk" + (card.get("data-res_url") or ""),
                "m": [], "days": [], "slots": [], "L": False, "D": False, "allSold": True,
            }
        menu_el = card.select_one(".dw-card-menu .lang_danish") or card.select_one(".dw-card-menu")
        menu_txt = text(menu_el)
        price = PRICE_RE.search(menu_txt)
        mtype = next((MENU_CLASS[c] for c in cls if c in MENU_CLASS), menu_txt.split("·")[0].strip())
        sold = (card.get("data-udsolgt") or "0").strip() == "1"
        if not any(m["t"] == mtype for m in a["m"]):
            a["m"].append({"t": mtype, "p": int(price.group(1)) if price else None})
        a["allSold"] = a["allSold"] and sold
        if "frokost" in cls:
            a["L"] = True
        if "aften" in cls:
            a["D"] = True
        seen = {tuple(s) for s in a["slots"]}
        for c in cls:
            m = DATE_RE.match(c)
            if m and int(m.group(1)) not in a["days"]:
                a["days"].append(int(m.group(1)))
            m = SLOT_RE.match(c)
            if m:
                s = (int(m.group(1)), int(m.group(2)), "L" if m.group(3) == "frokost" else "D")
                if s not in seen:
                    seen.add(s)
                    a["slots"].append(list(s))
    for a in agg.values():
        a["days"].sort()
    return agg


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "availability.json")
    agg = parse(fetch())
    if len(agg) < 50:
        sys.exit(f"Only {len(agg)} restaurants parsed; the site layout may have changed. Not publishing.")
    data = {"ts": int(time.time() * 1000), "source": URL, "agg": agg}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    sold = sum(1 for a in agg.values() if a["allSold"])
    print(f"Wrote {out}: {len(agg)} restaurants, {sold} fully sold out, "
          f"{sum(len(a['slots']) for a in agg.values())} bookable slots.")


if __name__ == "__main__":
    main()
