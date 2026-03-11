#!/usr/bin/env python3
"""
Generate BLS LAUS county series entries for ALL US counties and merge them
into bls_series.json.

Data source: US Census Bureau FIPS API (no key required).
Series pattern: LAUCN{5-digit-county-fips}0000000{measure}
  measure 003 = Unemployment Rate
  measure 005 = Employment Level
  measure 006 = Labor Force

Usage:
    # All states
    python scripts/generate_county_series.py

    # Single state (name or 2-digit FIPS)
    python scripts/generate_county_series.py --state ohio
    python scripts/generate_county_series.py --state 39

    # Preview without writing
    python scripts/generate_county_series.py --state ohio --dry-run
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

# ── paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
BLS_SERIES_JSON = REPO_ROOT / "src" / "core" / "configs" / "bls_series.json"

# ── Census FIPS API ────────────────────────────────────────────────────────────
CENSUS_COUNTY_URL = (
    "https://api.census.gov/data/2020/dec/pl"
    "?get=NAME&for=county:*&in=state:*"
)

# ── FIPS reference maps ────────────────────────────────────────────────────────
# 2-digit state FIPS → (full name, 2-letter abbreviation)
STATE_FIPS_MAP: dict[str, tuple[str, str]] = {
    "01": ("Alabama", "AL"),        "02": ("Alaska", "AK"),
    "04": ("Arizona", "AZ"),        "05": ("Arkansas", "AR"),
    "06": ("California", "CA"),     "08": ("Colorado", "CO"),
    "09": ("Connecticut", "CT"),    "10": ("Delaware", "DE"),
    "11": ("District of Columbia", "DC"), "12": ("Florida", "FL"),
    "13": ("Georgia", "GA"),        "15": ("Hawaii", "HI"),
    "16": ("Idaho", "ID"),          "17": ("Illinois", "IL"),
    "18": ("Indiana", "IN"),        "19": ("Iowa", "IA"),
    "20": ("Kansas", "KS"),         "21": ("Kentucky", "KY"),
    "22": ("Louisiana", "LA"),      "23": ("Maine", "ME"),
    "24": ("Maryland", "MD"),       "25": ("Massachusetts", "MA"),
    "26": ("Michigan", "MI"),       "27": ("Minnesota", "MN"),
    "28": ("Mississippi", "MS"),    "29": ("Missouri", "MO"),
    "30": ("Montana", "MT"),        "31": ("Nebraska", "NE"),
    "32": ("Nevada", "NV"),         "33": ("New Hampshire", "NH"),
    "34": ("New Jersey", "NJ"),     "35": ("New Mexico", "NM"),
    "36": ("New York", "NY"),       "37": ("North Carolina", "NC"),
    "38": ("North Dakota", "ND"),   "39": ("Ohio", "OH"),
    "40": ("Oklahoma", "OK"),       "41": ("Oregon", "OR"),
    "42": ("Pennsylvania", "PA"),   "44": ("Rhode Island", "RI"),
    "45": ("South Carolina", "SC"), "46": ("South Dakota", "SD"),
    "47": ("Tennessee", "TN"),      "48": ("Texas", "TX"),
    "49": ("Utah", "UT"),           "50": ("Vermont", "VT"),
    "51": ("Virginia", "VA"),       "53": ("Washington", "WA"),
    "54": ("West Virginia", "WV"),  "55": ("Wisconsin", "WI"),
    "56": ("Wyoming", "WY"),        "72": ("Puerto Rico", "PR"),
}

# Reverse map: normalised state name / abbrev → FIPS
_STATE_NAME_TO_FIPS: dict[str, str] = {}
for _fips, (_name, _abbr) in STATE_FIPS_MAP.items():
    _STATE_NAME_TO_FIPS[_name.lower()] = _fips
    _STATE_NAME_TO_FIPS[_abbr.lower()] = _fips
    _STATE_NAME_TO_FIPS[_fips] = _fips  # "39" → "39"


def resolve_state_fips(state_arg: str) -> str:
    """Return 2-digit FIPS string or raise."""
    key = state_arg.strip().lower()
    fips = _STATE_NAME_TO_FIPS.get(key)
    if not fips:
        raise ValueError(
            f"Unknown state '{state_arg}'. "
            f"Use full name, 2-letter abbreviation, or 2-digit FIPS."
        )
    return fips


# ── helpers ────────────────────────────────────────────────────────────────────

def _slug(county_name: str, state_abbr: str) -> str:
    """
    Build a stable JSON key like 'cuyahoga_oh' from 'Cuyahoga County' + 'OH'.
    Strips ' County', ' Parish', ' Borough', ' Census Area', ' Municipality',
    normalises unicode lookalikes, lowercases, and replaces spaces with '_'.
    """
    name = county_name
    # Remove trailing geographic suffixes
    for suffix in (
        " county", " parish", " borough", " census area",
        " municipality", " city and borough", " city",
    ):
        if name.lower().endswith(suffix):
            name = name[: len(name) - len(suffix)]
            break
    name = re.sub(r"[^a-z0-9 ]", "", name.lower())
    name = re.sub(r"\s+", "_", name.strip())
    return f"{name}_{state_abbr.lower()}"


def _series_ids(state_fips: str, county_code: str) -> dict[str, str]:
    """Build the three LAUS series IDs for a county."""
    fips5 = f"{state_fips}{county_code}"
    return {
        "unemployment_rate_series_id": f"LAUCN{fips5}0000000003",
        "employment_level_series_id":  f"LAUCN{fips5}0000000005",
        "labor_force_series_id":       f"LAUCN{fips5}0000000006",
    }


# ── Census fetch ───────────────────────────────────────────────────────────────

def fetch_census_counties(retries: int = 3) -> list[dict]:
    """
    Returns a list of dicts with keys:
        name, county_name, state_fips, county_code, fips5, state_name, state_abbr
    """
    print("Fetching county FIPS from Census Bureau …", flush=True)
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(CENSUS_COUNTY_URL, timeout=30)
            resp.raise_for_status()
            rows = resp.json()
            break
        except Exception as exc:
            if attempt == retries:
                raise RuntimeError(f"Census API failed after {retries} attempts: {exc}")
            print(f"  Attempt {attempt} failed ({exc}), retrying …")
            time.sleep(2 ** attempt)

    # rows[0] is the header: ["NAME", "state", "county"]
    headers = rows[0]
    name_idx   = headers.index("NAME")
    state_idx  = headers.index("state")
    county_idx = headers.index("county")

    counties = []
    for row in rows[1:]:
        raw_name   = row[name_idx]    # e.g. "Cuyahoga County, Ohio"
        state_fips = row[state_idx]   # e.g. "39"
        county_code = row[county_idx] # e.g. "035"

        if state_fips not in STATE_FIPS_MAP:
            continue  # skip territories we don't track

        state_name, state_abbr = STATE_FIPS_MAP[state_fips]

        # Census NAME is "County Name, State Name" – extract county part
        county_name = raw_name.split(",")[0].strip()

        counties.append({
            "county_name": county_name,
            "state_fips":  state_fips,
            "county_code": county_code,
            "fips5":       f"{state_fips}{county_code}",
            "state_name":  state_name,
            "state_abbr":  state_abbr,
        })

    print(f"  Fetched {len(counties)} counties across {len(STATE_FIPS_MAP)} states/territories.")
    return counties


# ── JSON merge ─────────────────────────────────────────────────────────────────

def build_county_entry(c: dict) -> dict:
    """Build the bls_series.json county entry for a single county."""
    entry = {
        "fips":       c["fips5"],
        "name":       c["county_name"],
        "state":      c["state_name"],
        "state_fips": c["state_fips"],
    }
    entry.update(_series_ids(c["state_fips"], c["county_code"]))
    return entry


def merge_into_series_json(
    counties: list[dict],
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Merge generated county entries into bls_series.json.

    Returns (added, updated) counts.
    """
    with open(BLS_SERIES_JSON, "r") as f:
        config = json.load(f)

    existing_county = config.get("county", {})

    # Preserve non-county keys (note, series_codes, etc.)
    preserved_keys = {
        k: v for k, v in existing_county.items()
        if not isinstance(v, dict) or "fips" not in v
    }

    added = updated = 0
    new_county: dict = {}

    for c in counties:
        key = _slug(c["county_name"], c["state_abbr"])
        entry = build_county_entry(c)

        if key in existing_county and isinstance(existing_county[key], dict):
            # Update series IDs but keep any extra fields the user may have added
            old = existing_county[key]
            merged = {**old, **entry}
            new_county[key] = merged
            if merged != old:
                updated += 1
            else:
                new_county[key] = old
        else:
            new_county[key] = entry
            added += 1

    # Re-attach preserved non-entry keys (e.g. "note")
    new_county.update(preserved_keys)

    config["county"] = new_county

    if dry_run:
        print(f"\n[dry-run] Would write {added} new + {updated} updated entries.")
        # Print a sample
        sample = [k for k, v in new_county.items() if isinstance(v, dict) and "fips" in v][:3]
        for k in sample:
            print(f"  {k}: {json.dumps(new_county[k])}")
    else:
        with open(BLS_SERIES_JSON, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nWrote {added} new + {updated} updated county entries to bls_series.json")

    return added, updated


# ── main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate bls_series.json county section from Census FIPS data"
    )
    parser.add_argument(
        "--state",
        default=None,
        help="Limit to one state (full name, abbreviation, or 2-digit FIPS). "
             "Omit to generate all states.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without modifying bls_series.json",
    )
    args = parser.parse_args()

    # Resolve optional state filter
    state_fips_filter: str | None = None
    if args.state:
        try:
            state_fips_filter = resolve_state_fips(args.state)
            state_name = STATE_FIPS_MAP[state_fips_filter][0]
            print(f"Filtering to: {state_name} (FIPS {state_fips_filter})")
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1

    # Fetch all counties (one API call regardless of filter)
    all_counties = fetch_census_counties()

    # Apply state filter
    if state_fips_filter:
        counties = [c for c in all_counties if c["state_fips"] == state_fips_filter]
        print(f"  Filtered to {len(counties)} counties in {STATE_FIPS_MAP[state_fips_filter][0]}.")
    else:
        counties = all_counties

    if not counties:
        print("No counties matched. Nothing to write.")
        return 1

    added, updated = merge_into_series_json(counties, dry_run=args.dry_run)

    if not args.dry_run:
        total = added + updated
        print(
            f"\nDone. {total} county entries in bls_series.json "
            f"({added} new, {updated} refreshed)."
        )
        print(
            "\nNext: re-run initialize_data.py to push county data into the vector store."
        )
        if state_fips_filter:
            abbr = STATE_FIPS_MAP[state_fips_filter][1].lower()
            print(f"  python scripts/initialize_data.py --state {abbr} --county-only")
        else:
            print("  python scripts/initialize_data.py --county-only")

    return 0


if __name__ == "__main__":
    sys.exit(main())
