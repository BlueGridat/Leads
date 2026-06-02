# BlueGrid Leads

Master lead pipeline for BlueGrid — local businesses we can sell websites to.

**`leads.csv` is the go-to spreadsheet.** Open it in Excel or Google Sheets. It contains
**only qualified leads**: local businesses that **need a website** and that we can **actually reach**.

## Current data: Greater Linz — 182 qualified leads

| Niche | Leads |
|-------|-------|
| Dentist | 14 |
| Doctor / Medical | 79 |
| Veterinarian | 6 |
| Physiotherapist | 3 |
| Optician | 2 |
| Hair / Barber | 42 |
| Beauty / Nails | 9 |
| Massage / Wellness | 12 |
| Fitness / Gym | 2 |
| Trades (plumber, carpenter, painter, tiler, joiner, metalwork, gardener) | 13 |
| **TOTAL** | **182** |

Leads are ordered **dentists first, then doctors/medical, then the other niches**.
`leads.md` is a human-readable version of the same data, grouped by niche, for quick viewing on GitHub.

## What "qualified" means

A business is included in the spreadsheet only if **all** of these are true:

1. **It needs a site** — it has *no website at all*, or its website is *broken / unreachable*.
2. **We can reach it** — it has a phone number, an email, or a real street address.
3. It is a real, named business in a niche our template can serve.

Businesses that already have a working website are excluded (they are not leads).

## Spreadsheet columns

| Column | Meaning |
|--------|---------|
| `Priority` | `HOT` = broken site (easiest sale) · `WARM` = has phone/email · `COOL` = visit/mail only |
| `Niche` | Business category |
| `Business Name` | Name as listed in OpenStreetMap |
| `Website Status` | `No website` or `Broken website` |
| `Phone` / `Email` | Contact details (where available) |
| `Full Address` | Street + number + postcode + town in one line (for in-person visits) |
| `Street` / `Postcode` / `Town` | Address parts (split out for sorting/filtering) |
| `Google Maps Link` | Tap-to-navigate map pin (from exact coordinates) — for driving to the business |
| `Source URL (if broken)` | The dead/broken site (use as the opener: "your site is down") |
| `Notes` | HTTP error for broken sites |
| `Outreach Status` | Pipeline tracking — start as `Not contacted`, then `Contacted`, `Replied`, `Meeting`, `Won`, `Lost` |
| `Owner` | Who on the team owns this lead |
| `Next Action` / `Last Contacted` | Your follow-up tracking |

## Priority playbook

1. **HOT (broken site):** They already pay for a domain/site that's now down. Open with
   "I noticed your website is offline." Highest conversion.
2. **WARM (phone/email):** Direct outreach. Dentists & doctors first — high margin, and the
   BlueGrid dental template is a near-finished demo for them.
3. **COOL (address only):** Walk-in route or postal mailer.

> **Austria compliance note (§107 TKG):** Unsolicited marketing emails and cold calls — even
> B2B — are restricted without prior consent. Prefer **in-person visits** and **postal mail**
> (Werbepost), or use the broken-site as a legitimate reason for first contact. Get legal sign-off
> before any cold email campaign.

## How to regenerate / add more cities

Requires Python 3 (standard library only — no pip installs needed).

```bash
# 1. Scrape real businesses for a region (edit REGION + BBOX in the script)
python3 tools/scrape_leads.py        # writes data/<region>_raw.json

# 2. Build the qualified spreadsheet from the raw data
python3 tools/build_spreadsheet.py   # writes leads.csv + leads.md
```

To target another city (Wels, Steyr, Graz, Salzburg…), change `REGION` and `BBOX` near the top of
`tools/scrape_leads.py`, then re-run both scripts. To target different niches, edit the `FILTERS`
list in the scraper and the `NICHE` map in the builder.

## Data source & disclaimer

Business data comes from **OpenStreetMap**, © OpenStreetMap contributors, licensed under the
[ODbL](https://www.openstreetmap.org/copyright). It may be incomplete or out of date —
**always verify a contact before reaching out.** "No website" means no website was listed in
OpenStreetMap; a business may still have a social-media page or an unlisted site.
