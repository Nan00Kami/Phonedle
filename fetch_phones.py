import json
import re
import requests

SPARQL_URL = "https://query.wikidata.org/sparql"

QUERY = """
SELECT DISTINCT ?phoneLabel ?brandLabel ?year ?osLabel WHERE {
  VALUES ?type { wd:Q1140645 wd:Q22645 }
  ?phone wdt:P31 ?type .
  ?phone wdt:P176 ?brand .
  ?phone wdt:P577 ?date .
  BIND(YEAR(?date) AS ?year)
  FILTER(?year >= 2000 && ?year <= 2026)
  OPTIONAL { ?phone wdt:P306 ?os . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
ORDER BY ?year
LIMIT 1200
"""

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

def main():
    headers = {"User-Agent": "PhonleBot/1.0 (browser-build)"}
    res = requests.get(SPARQL_URL, params={"query": QUERY, "format": "json"}, headers=headers)
    res.raise_for_status()
    data = res.json()

    results = []
    seen = set()

    for item in data["results"]["bindings"]:
        name = item.get("phoneLabel", {}).get("value", "").strip()
        brand = item.get("brandLabel", {}).get("value", "").strip()
        year_str = item.get("year", {}).get("value", "0")
        os_raw = item.get("osLabel", {}).get("value", "")

        if re.match(r"^Q\d+$", name) or not name or len(name) < 3:
            continue

        year = int(year_str)
        if name.lower() not in seen:
            seen.add(name.lower())
            results.append({
                "name": name,
                "brand": brand if brand and not brand.startswith("Q") else "Generic",
                "year": year,
                "os": clean_os(os_raw, year),
                "form": infer_form_factor(name)
            })

    with open("phones.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
