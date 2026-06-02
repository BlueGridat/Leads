#!/usr/bin/env python3
"""
Build the BlueGrid master leads spreadsheet from scraped raw data.

QUALIFICATION RULES (a lead is included only if ALL are true):
  1. Needs a site:   Tier A (no website) OR Tier B (broken website)
  2. Reachable:      has a phone OR an email OR a real street address
  3. Real business:  has a name (already guaranteed by scraper)

Ordering: dentists first, then doctors/medical, then the other niches.
Within each niche: broken-site leads first (hottest), then by contactability.

Outputs:
  - leads.csv   (the master spreadsheet — open in Excel / Google Sheets)
  - leads.md    (readable summary table for GitHub)
"""

import json
import csv
import urllib.parse

RAW = "/projects/sandbox/Leads/data/linz_raw.json"
CSV_OUT = "/projects/sandbox/Leads/leads.csv"
MD_OUT = "/projects/sandbox/Leads/leads.md"

# Niche display label + ordering priority (lower = earlier in sheet)
NICHE = {
    "amenity=dentist": ("Dentist", 1),
    "healthcare=dentist": ("Dentist", 1),
    "amenity=doctors": ("Doctor / Medical", 2),
    "healthcare=doctor": ("Doctor / Medical", 2),
    "amenity=clinic": ("Doctor / Medical", 2),
    "healthcare=clinic": ("Doctor / Medical", 2),
    "healthcare=alternative": ("Alternative Medicine", 3),
    "healthcare=physiotherapist": ("Physiotherapist", 4),
    "amenity=veterinary": ("Veterinarian", 5),
    "shop=optician": ("Optician", 6),
    "shop=hairdresser": ("Hair / Barber", 7),
    "shop=beauty": ("Beauty / Nails", 8),
    "shop=massage": ("Massage / Wellness", 9),
    "leisure=fitness_centre": ("Fitness / Gym", 10),
    "craft=electrician": ("Trade - Electrician", 11),
    "craft=plumber": ("Trade - Plumber", 11),
    "craft=hvac": ("Trade - HVAC", 11),
    "craft=carpenter": ("Trade - Carpenter", 11),
    "craft=joiner": ("Trade - Joiner", 11),
    "craft=painter": ("Trade - Painter", 11),
    "craft=tiler": ("Trade - Tiler", 11),
    "craft=roofer": ("Trade - Roofer", 11),
    "craft=plasterer": ("Trade - Plasterer", 11),
    "craft=locksmith": ("Trade - Locksmith", 11),
    "craft=glaziery": ("Trade - Glazier", 11),
    "craft=gardener": ("Trade - Gardener", 11),
    "craft=metal_construction": ("Trade - Metalwork", 11),
    "craft=stonemason": ("Trade - Stonemason", 11),
}


def has_real_address(r):
    # A street name (with or without number) makes the lead visitable.
    return bool(r["street"].strip())


def reachable(r):
    return bool(r["phone"]) or bool(r["email"]) or has_real_address(r)


def contact_score(r):
    s = 0
    if r["phone"]:
        s += 3
    if r["email"]:
        s += 2
    if has_real_address(r):
        s += 1
    return s


def priority(r):
    # Hottest = broken site + reachable; then no-site with phone; then the rest.
    if r["tier"] == "B_broken_website":
        return "HOT - broken site"
    if r["phone"] or r["email"]:
        return "WARM - direct contact"
    return "COOL - visit/mail"


def full_street(r):
    """Just street + house number (no town)."""
    line = r["street"]
    if r["housenumber"]:
        line = f"{line} {r['housenumber']}".strip()
    return line


def full_address(r):
    """Street + number, postcode + town — a single human-readable address line."""
    line = full_street(r)
    town_part = " ".join(x for x in [r.get("postcode", ""), r.get("town", "")] if x).strip()
    if line and town_part:
        return f"{line}, {town_part}"
    return line or town_part


def maps_link(r):
    """Tap-to-navigate Google Maps URL. Prefer exact coordinates, else address/name search."""
    lat, lon = r.get("lat"), r.get("lon")
    if lat is not None and lon is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    query = full_address(r) or r["name"]
    if r.get("town") and r["town"] not in query:
        query = f"{query} {r['town']}"
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query)


def main():
    with open(RAW, encoding="utf-8") as fh:
        rows = json.load(fh)

    leads = [r for r in rows
             if r["tier"] in ("A_no_website", "B_broken_website") and reachable(r)]

    for r in leads:
        label, order = NICHE.get(r["category"], ("Other", 99))
        r["_niche"] = label
        r["_order"] = order
        r["_tierrank"] = 0 if r["tier"] == "B_broken_website" else 1
        r["_score"] = contact_score(r)

    leads.sort(key=lambda r: (r["_order"], r["_tierrank"], -r["_score"], r["name"].lower()))

    headers = [
        "Priority", "Niche", "Business Name", "Website Status",
        "Phone", "Email",
        "Full Address", "Street", "Postcode", "Town", "Google Maps Link",
        "Source URL (if broken)", "Notes",
        "Outreach Status", "Owner", "Next Action", "Last Contacted",
    ]

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for r in leads:
            status = "No website" if r["tier"] == "A_no_website" else "Broken website"
            w.writerow([
                priority(r), r["_niche"], r["name"], status,
                r["phone"], r["email"],
                full_address(r), full_street(r), r["postcode"],
                r["town"] or "Linz area", maps_link(r),
                r["website"] if r["tier"] == "B_broken_website" else "",
                r["web_detail"] if r["tier"] == "B_broken_website" else "",
                "Not contacted", "", "", "",
            ])

    # Readable markdown summary (grouped by niche)
    from collections import Counter, defaultdict
    by_niche = defaultdict(list)
    for r in leads:
        by_niche[(r["_order"], r["_niche"])].append(r)

    md = ["# BlueGrid Master Leads - Greater Linz",
          "",
          "_Qualified leads only: businesses with **no website** or a **broken website** that we can reach "
          "(phone, email, or street address). Source: OpenStreetMap (c) OpenStreetMap contributors, ODbL. "
          "**Verify each contact before outreach.**_",
          "",
          f"**Total qualified leads: {len(leads)}**",
          ""]

    cnt = Counter(r["_niche"] for r in leads)
    md.append("| Niche | Qualified leads |")
    md.append("|-------|-----------------|")
    for (order, niche) in sorted(by_niche.keys()):
        md.append(f"| {niche} | {len(by_niche[(order, niche)])} |")
    md.append(f"| **TOTAL** | **{len(leads)}** |")
    md.append("")

    for (order, niche) in sorted(by_niche.keys()):
        group = by_niche[(order, niche)]
        md.append(f"## {niche} ({len(group)})")
        md.append("")
        md.append("| Priority | Business | Status | Phone | Email | Address | Map |")
        md.append("|----------|----------|--------|-------|-------|---------|-----|")
        for r in group:
            status = "No site" if r["tier"] == "A_no_website" else "BROKEN"
            addr = full_address(r) or "—"
            md.append(
                f"| {priority(r)} | {r['name']} | {status} | {r['phone'] or '—'} "
                f"| {r['email'] or '—'} | {addr} | [map]({maps_link(r)}) |"
            )
        md.append("")

    with open(MD_OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))

    print(f"Qualified leads: {len(leads)}")
    for (order, niche) in sorted(by_niche.keys()):
        print(f"  {niche}: {len(by_niche[(order, niche)])}")
    print(f"\nWrote:\n  {CSV_OUT}\n  {MD_OUT}")


if __name__ == "__main__":
    main()
