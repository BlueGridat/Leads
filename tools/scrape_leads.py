#!/usr/bin/env python3
"""
BlueGrid Lead Scraper
---------------------
Pulls REAL local businesses from OpenStreetMap (Overpass API) for a geographic
bounding box, then classifies each by website status so we can qualify leads.

Tier A = no website tag at all        -> needs a site (prime lead)
Tier B = has website but it's broken   -> rebuild pitch (hottest lead)
Tier C = has a working website         -> not a lead (skip in pipeline)

Output: data/<region>_raw.json  (full records, all tiers)

Data source: OpenStreetMap, (c) OpenStreetMap contributors, ODbL.
Always verify each contact before outreach.
"""

import json
import sys
import urllib.request
import urllib.parse
import urllib.error
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

# Greater Linz metro bounding box (south, west, north, east)
# Covers Linz + Leonding, Traun, Ansfelden, Pasching, Pucking, Engerwitzdorf edges.
REGION = "linz"
BBOX = (48.20, 14.12, 48.43, 14.46)

# Business categories we can serve with the BlueGrid template (ICP).
FILTERS = [
    # Dental / medical
    ('amenity', 'dentist'),
    ('healthcare', 'dentist'),
    ('amenity', 'doctors'),
    ('healthcare', 'doctor'),
    ('amenity', 'clinic'),
    ('healthcare', 'clinic'),
    ('healthcare', 'physiotherapist'),
    ('healthcare', 'alternative'),
    ('amenity', 'veterinary'),
    # Personal care / wellness
    ('shop', 'hairdresser'),
    ('shop', 'beauty'),
    ('shop', 'massage'),
    ('shop', 'optician'),
    ('leisure', 'fitness_centre'),
    # Trades
    ('craft', 'electrician'),
    ('craft', 'plumber'),
    ('craft', 'hvac'),
    ('craft', 'carpenter'),
    ('craft', 'joiner'),
    ('craft', 'painter'),
    ('craft', 'tiler'),
    ('craft', 'roofer'),
    ('craft', 'plasterer'),
    ('craft', 'locksmith'),
    ('craft', 'glaziery'),
    ('craft', 'gardener'),
    ('craft', 'metal_construction'),
    ('craft', 'stonemason'),
]


def build_query():
    s, w, n, e = BBOX
    parts = []
    for k, v in FILTERS:
        for elem in ('node', 'way'):
            parts.append(f'{elem}["{k}"="{v}"]({s},{w},{n},{e});')
    body = "\n".join(parts)
    return f"[out:json][timeout:120];\n(\n{body}\n);\nout center tags;"


def fetch_overpass():
    data = urllib.parse.urlencode({"data": build_query()}).encode()
    last_err = None
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "User-Agent": "BlueGridLeadScraper/1.0 (agency lead research)",
                    "Accept": "application/json,*/*",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                print(f"  (using {url})", file=sys.stderr)
                return json.loads(resp.read().decode())
        except Exception as e:
            last_err = e
            print(f"  mirror failed: {url} -> {type(e).__name__}: {e}", file=sys.stderr)
    raise RuntimeError(f"All Overpass mirrors failed. Last: {last_err}")


def category_of(tags):
    for k, v in FILTERS:
        if tags.get(k) == v:
            return f"{k}={v}"
    return "other"


def check_website(url):
    if not url:
        return ("none", "")
    test = url if url.startswith("http") else "http://" + url
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(
            test, headers={"User-Agent": "Mozilla/5.0 (lead-check)"}, method="GET"
        )
        with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
            code = r.getcode()
            return ("ok", f"HTTP {code}") if code and code < 400 else ("broken", f"HTTP {code}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            return ("ok", f"HTTP {e.code} (protected)")
        return ("broken", f"HTTP {e.code}")
    except Exception as e:
        return ("broken", f"{type(e).__name__}")


def main():
    print(f"Querying OSM for greater {REGION.title()} ...", file=sys.stderr)
    raw = fetch_overpass()
    elements = raw.get("elements", [])
    print(f"Got {len(elements)} raw elements.", file=sys.stderr)

    seen, rows = set(), []
    for el in elements:
        t = el.get("tags", {})
        name = t.get("name")
        if not name:
            continue
        key = name.strip().lower()
        if key in seen:
            continue
        seen.add(key)

        # Coordinates: nodes have lat/lon directly; ways/relations have a "center".
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is None and "center" in el:
            lat = el["center"].get("lat")
            lon = el["center"].get("lon")

        rows.append({
            "name": name.strip(),
            "category": category_of(t),
            "street": t.get("addr:street", ""),
            "housenumber": t.get("addr:housenumber", ""),
            "postcode": t.get("addr:postcode", ""),
            "town": t.get("addr:city", ""),
            "lat": lat,
            "lon": lon,
            "phone": t.get("phone") or t.get("contact:phone") or "",
            "email": t.get("email") or t.get("contact:email") or "",
            "website": t.get("website") or t.get("contact:website") or t.get("url") or "",
        })

    print(f"{len(rows)} unique named businesses. Checking website health ...", file=sys.stderr)

    def worker(row):
        status, detail = check_website(row["website"])
        row["web_status"], row["web_detail"] = status, detail
        return row

    with ThreadPoolExecutor(max_workers=20) as ex:
        for f in as_completed([ex.submit(worker, r) for r in rows]):
            f.result()

    for r in rows:
        r["tier"] = ("B_broken_website" if r["web_status"] == "broken"
                     else "A_no_website" if r["web_status"] == "none"
                     else "C_working_website")

    out = f"/projects/sandbox/Leads/data/{REGION}_raw.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2)

    a = sum(1 for r in rows if r["tier"] == "A_no_website")
    b = sum(1 for r in rows if r["tier"] == "B_broken_website")
    c = sum(1 for r in rows if r["tier"] == "C_working_website")
    print(f"\nTier A (no website):     {a}")
    print(f"Tier B (broken website): {b}")
    print(f"Tier C (working):        {c}")
    print(f"TOTAL: {len(rows)}  ->  {out}")


if __name__ == "__main__":
    main()
