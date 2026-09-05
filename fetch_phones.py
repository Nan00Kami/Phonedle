import json
import re
import time
import requests

SPARQL_URL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "PhonleFullDBBuilder/2.0 (GitHubActions)"}

def clean_os(os_raw, year):
    if not os_raw or os_raw.startswith("Q"):
        return "Android" if year >= 2010 else "Proprietary"
    os_lower = os_raw.lower()
    if "android" in os_lower:
        return "Android"
    if any(k in os_lower for k in ["ios", "iphone os"]):
        return "iOS"
    if "windows" in os_lower:
        return "Windows Phone"
    if "symbian" in os_lower:
        return "Symbian"
    if "blackberry" in os_lower:
        return "BlackBerry OS"
    return "Proprietary"

def infer_form_factor(name):
    name_lower = name.lower()
    if any(k in name_lower for k in ["fold", "flip", "razr", "clamshell"]):
        return "Foldable" if "fold" in name_lower else "Flip"
    if any(k in name_lower for k in ["slide", "slider", "sidekick"]):
        return "Slider"
    if any(k in name_lower for k in ["qwerty", "bold", "curve", "blackberry"]):
        return "QWERTY Bar"
    return "Bar"

def fetch_year(year):
    # Lean, unjoined query targeted at a single year to guarantee sub-second execution
    query = f"""
    SELECT DISTINCT ?phoneLabel ?brandLabel ?osLabel WHERE {{
      VALUES ?type {{ wd:Q1140645 wd:Q22645 }}
      ?phone wdt:P31 ?type .
      ?phone wdt:P577 ?date .
      FILTER(YEAR(?date) = {year})
      OPTIONAL {{ ?phone wdt:P176 ?brand . }}
      OPTIONAL {{ ?phone wdt:P306 ?os . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    try:
        res = requests.get(SPARQL_URL, params={"query": query, "format": "json"}, headers=HEADERS, timeout=45)
        res.raise_for_status()
        return res.json().get("results", {}).get("bindings", [])
    except Exception as e:
        print(f"Warning: Year {year} encountered an error: {e}")
        return []

def main():
    all_phones = []
    seen = set()

    print("Fetching phone records from 2000 to 2026...")
    for year in range(2000, 2027):
        print(f"Querying models for {year}...")
        records = fetch_year(year)
        
        for item in records:
            name = item.get("phoneLabel", {}).get("value", "").strip()
            brand = item.get("brandLabel", {}).get("value", "Generic").strip()
            os_raw = item.get("osLabel", {}).get("value", "")

            # Filter out blank labels, raw Wikidata Q-codes, or non-phone metadata
            if not name or re.match(r"^Q\d+$", name) or len(name) < 2:
                continue

            brand_clean = "Generic" if re.match(r"^Q\d+$", brand) else brand

            # Deduplicate items
            key = (name.lower(), year)
            if key not in seen:
                seen.add(key)
                all_phones.append({
                    "name": name,
                    "brand": brand_clean,
                    "year": year,
                    "os": clean_os(os_raw, year),
                    "form": infer_form_factor(name)
                })
        
        # Respect Wikidata API rate-limit etiquette between chunked iterations
        time.sleep(1.2)

    # Sort lexicographically by name
    all_phones.sort(key=lambda x: (x["year"], x["name"]))

    print(f"Extraction complete. Writing {len(all_phones)} devices to phones.json...")
    with open("phones.json", "w", encoding="utf-8") as f:
        json.dump(all_phones, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
