#!/usr/bin/env python3
"""
Build the COMPLETE dentist roster for the greater Linz area.

Unlike leads.csv (which contains only qualified leads = businesses that need a
website), this file lists EVERY dentist found in OpenStreetMap regardless of
website status, so the whole market can be reviewed one by one.

Sort order: Linz proper first (town == Linz or postcode 40xx), then surrounding
towns; within each, "needs a website" first, then by name.

Outputs:
  - dentists_linz_all.csv
  - dentists_linz_all.md
"""

import json
import csv
import urllib.parse

RAW = "/projects/sandbox/Leads/data/linz_raw.json"
CSV_OUT = "/projects/sandbox/Leads/dentists_linz_all.csv"
MD_OUT = "/projects/sandbox/Leads/dentists_linz_all.md"

DENTIST_CATS = ("amenity=dentist", "healthcare=dentist")


def full_street(r):
    line = r["street"]
    if r["housenumber"]:
        line = f"{line} {r['housenumber']}".strip()
    return line


def full_address(r):
    line = full_street(r)
    town_part = " ".join(x for x in [r.get("postcode", ""), r.get("town", "")] if x).strip()
    if line and town_part:
        return f"{line}, {town_part}"
    return line or town_part


def maps_link(r):
    lat, lon = r.get("lat"), r.get("lon")
    if lat is not None and lon is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    query = full_address(r) or r["name"]
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query)


def status_label(tier):
    return {
        "A_no_website": "No website",
        "B_broken_website": "Broken website",
        "C_working_website": "Has website",
    }[tier]


# Linz city postal codes (4020/4030/4040 cover the city; 4010/4017/4021 are special-use).
# 4050 = Traun, 4060 = Leonding, 4061 = Pasching, 4210 = Gallneukirchen, etc.
LINZ_CODES = {"4020", "4021", "4030", "4040", "4010", "4017"}


def is_linz_proper(r):
    town = (r.get("town") or "").strip().lower()
    if town:
        return town == "linz"
    pc = (r.get("postcode") or "").strip()
    if pc:
        return pc in LINZ_CODES
    return True  # no town and no postcode -> default to "Linz area"


def needs_site_rank(tier):
    return {"B_broken_website": 0, "A_no_website": 1, "C_working_website": 2}[tier]


def main():
    with open(RAW, encoding="utf-8") as fh:
        rows = json.load(fh)

    dents = [r for r in rows if r["category"] in DENTIST_CATS]

    for r in dents:
        r["_linz"] = 0 if is_linz_proper(r) else 1
        r["_rank"] = needs_site_rank(r["tier"])

    dents.sort(key=lambda r: (r["_linz"], r["_rank"], r["name"].lower()))

    headers = [
        "#", "Business Name", "Website Status", "Existing Website",
        "Phone", "Email", "Full Address", "Town", "Postcode",
        "Google Maps Link", "Is Lead?", "Notes",
        "Outreach Status", "Owner", "Next Action", "Last Contacted",
    ]

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(headers)
        for i, r in enumerate(dents, 1):
            is_lead = "Yes" if r["tier"] in ("A_no_website", "B_broken_website") else "No (has site)"
            notes = r["web_detail"] if r["tier"] == "B_broken_website" else ""
            w.writerow([
                i, r["name"], status_label(r["tier"]), r["website"],
                r["phone"], r["email"], full_address(r),
                r["town"] or "Linz area", r["postcode"],
                maps_link(r), is_lead, notes,
                "Not contacted", "", "", "",
            ])

    # Markdown view
    linz = [r for r in dents if r["_linz"] == 0]
    around = [r for r in dents if r["_linz"] == 1]

    def table(group):
        out = ["| # | Dentist | Status | Phone | Address | Existing Site | Map |",
               "|---|---------|--------|-------|---------|---------------|-----|"]
        for i, r in enumerate(group, 1):
            site = r["website"] if r["website"] else "—"
            out.append(
                f"| {i} | {r['name']} | {status_label(r['tier'])} | {r['phone'] or '—'} "
                f"| {full_address(r) or '—'} | {site} | [map]({maps_link(r)}) |"
            )
        return out

    md = ["# Complete Dentist Roster — Greater Linz",
          "",
          f"**Every dentist found in OpenStreetMap: {len(dents)}** "
          f"({sum(1 for r in dents if r['tier']!='C_working_website')} are leads / need a site, "
          f"{sum(1 for r in dents if r['tier']=='C_working_website')} already have a working site).",
          "",
          "_This is the full market for review — not just qualified leads. "
          "Source: OpenStreetMap (c) OpenStreetMap contributors, ODbL. "
          "OSM may be incomplete; verify each entry. 'No website' = none listed in OSM._",
          "",
          f"## In Linz ({len(linz)})", ""]
    md += table(linz)
    md += ["", f"## Surrounding towns ({len(around)})", ""]
    md += table(around)

    with open(MD_OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md))

    print(f"Total dentists: {len(dents)}  (Linz proper: {len(linz)}, surrounding: {len(around)})")
    leads = sum(1 for r in dents if r['tier'] != 'C_working_website')
    print(f"  Leads (need site): {leads}   Already have site: {len(dents)-leads}")
    print(f"Wrote:\n  {CSV_OUT}\n  {MD_OUT}")


if __name__ == "__main__":
    main()
