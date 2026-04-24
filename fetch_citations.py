"""
Google Scholar Citation Tracker — SerpAPI versie
Haalt dagelijks citaties op en slaat ze op in citations.csv
"""

import csv
import os
import time
from datetime import date
import urllib.request
import urllib.parse
import json

# ── Configuratie ────────────────────────────────────────────────────────────
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "JOUW_API_KEY_HIER")

AUTHORS = [
    {
        "name": "Kaj S. Emanuel",
        "author_id": "lepUM34AAAAJ",
        "search_query": "Kaj S. Emanuel"
    },
    {
        "name": "Laura Zwaan",
        "author_id": "CoLnfzkAAAAJ",
        "search_query": "Laura Zwaan"
    },
]

OUTPUT_FILE = "citations_combined.csv"
# ────────────────────────────────────────────────────────────────────────────


def serpapi_request(params: dict) -> dict:
    params["api_key"] = SERPAPI_KEY
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def find_author_id(query: str) -> str | None:
    """Zoek author_id op via Scholar Authors search."""
    try:
        data = serpapi_request({
            "engine": "google_scholar_author",
            "mauthors": query,
        })
        profiles = data.get("profiles", [])
        if profiles:
            author_id = profiles[0].get("author_id")
            print(f"  Gevonden author_id: {author_id}")
            return author_id
    except Exception as e:
        print(f"  Fout bij zoeken author_id: {e}")
    return None


def get_citation_count(author_config: dict) -> dict:
    result = {
        "name": author_config["name"],
        "citations": None,
        "h_index": None,
        "i10_index": None,
        "error": None
    }

    try:
        author_id = author_config.get("author_id")
        if not author_id:
            author_id = find_author_id(author_config["search_query"])

        if not author_id:
            result["error"] = "author_id niet gevonden"
            return result

        data = serpapi_request({
            "engine": "google_scholar_author",
            "author_id": author_id,
        })

        cited_by = data.get("cited_by", {})
        table = cited_by.get("table", [])

        # Citaties ophalen
        citations = None
        h_index = None
        i10_index = None

        for row in table:
            if "citations" in row:
                citations = row["citations"].get("all")
            if "h_index" in row:
                h_index = row["h_index"].get("all")
            if "i10_index" in row:
                i10_index = row["i10_index"].get("all")

        result["citations"] = citations
        result["h_index"] = h_index
        result["i10_index"] = i10_index

        print(f"✓ {author_config['name']}: {citations} citaties (h={h_index}, i10={i10_index})")

    except Exception as e:
        result["error"] = str(e)
        print(f"✗ {author_config['name']}: fout — {e}")

    return result


def save_to_csv(results: list, filename: str):
    today = date.today().isoformat()
    file_exists = os.path.isfile(filename)

    with open(filename, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["date", "name", "citations", "h_index", "i10_index", "error"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in results:
            writer.writerow({
                "date": today,
                "name": r["name"],
                "citations": r["citations"],
                "h_index": r["h_index"],
                "i10_index": r["i10_index"],
                "error": r.get("error", "")
            })

    print(f"✓ Opgeslagen in {filename}")


def main():
    print("=" * 50)
    print(f"Citation Tracker — {date.today().isoformat()}")
    print("=" * 50)

    if SERPAPI_KEY == "JOUW_API_KEY_HIER":
        print("⚠ Stel SERPAPI_KEY in als environment variable!")
        return

    results = []
    for i, author in enumerate(AUTHORS):
        print(f"\nOpvragen: {author['name']}...")
        result = get_citation_count(author)
        results.append(result)
        if i < len(AUTHORS) - 1:
            time.sleep(2)

    save_to_csv(results, OUTPUT_FILE)

    print("\n" + "=" * 50)
    print("Klaar!")
    for r in results:
        if r["citations"] is not None:
            print(f"  {r['name']}: {r['citations']} citaties")
        else:
            print(f"  {r['name']}: FOUT — {r['error']}")


if __name__ == "__main__":
    main()
