"""
Google Scholar Citation Tracker — SerpAPI versie
Haalt dagelijks citaties op en slaat ze op in citations.csv
Haalt periodiek (bij --papers flag) de volledige paperlijst op → papers_combined.csv
"""

import csv
import os
import time
import argparse
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
    },
    {
        "name": "Laura Zwaan",
        "author_id": "CoLnfzkAAAAJ",
    },
]

OUTPUT_FILE        = "citations_combined.csv"
OUTPUT_PAPERS_FILE = "papers_combined.csv"
# ────────────────────────────────────────────────────────────────────────────


def serpapi_request(params: dict) -> dict:
    params["api_key"] = SERPAPI_KEY
    url = "https://serpapi.com/search?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


# ── Dagelijkse citatiefetch ──────────────────────────────────────────────────

def get_citation_count(author: dict) -> dict:
    result = {
        "name": author["name"],
        "citations": None,
        "h_index": None,
        "i10_index": None,
        "error": None,
    }
    try:
        data = serpapi_request({
            "engine": "google_scholar_author",
            "author_id": author["author_id"],
        })
        for row in data.get("cited_by", {}).get("table", []):
            if "citations" in row:
                result["citations"] = row["citations"].get("all")
            if "h_index" in row:
                result["h_index"] = row["h_index"].get("all")
            if "i10_index" in row:
                result["i10_index"] = row["i10_index"].get("all")
        print(f"✓ {author['name']}: {result['citations']} citaties "
              f"(h={result['h_index']}, i10={result['i10_index']})")
    except Exception as e:
        result["error"] = str(e)
        print(f"✗ {author['name']}: fout — {e}")
    return result


def save_citations(results: list):
    today = date.today().isoformat()
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["date", "name", "citations", "h_index", "i10_index", "error"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for r in results:
            writer.writerow({
                "date":      today,
                "name":      r["name"],
                "citations": r["citations"],
                "h_index":   r["h_index"],
                "i10_index": r["i10_index"],
                "error":     r.get("error", ""),
            })
    print(f"✓ Citaties opgeslagen in {OUTPUT_FILE}")


# ── Paperlijst fetch (periodiek) ────────────────────────────────────────────

def get_papers(author: dict) -> list:
    """
    Haalt alle papers op via paginering (start=0, 20, 40, …).
    Geeft lijst van dicts terug met: author_id, title, year, citations.
    """
    papers = []
    start = 0
    page_size = 20

    while True:
        try:
            data = serpapi_request({
                "engine":    "google_scholar_author",
                "author_id": author["author_id"],
                "sort":      "pubdate",
                "start":     start,
            })
        except Exception as e:
            print(f"  Fout bij ophalen pagina start={start}: {e}")
            break

        articles = data.get("articles", [])
        if not articles:
            break

        for art in articles:
            papers.append({
                "author_id": author["author_id"],
                "name":      author["name"],
                "title":     art.get("title", ""),
                "year":      art.get("year", ""),
                "citations": art.get("cited_by", {}).get("value", 0),
                "link":      art.get("link", ""),
            })

        print(f"  {author['name']}: {len(papers)} papers opgehaald (pagina start={start})")

        # Stop als er minder dan een volle pagina terugkwam
        if len(articles) < page_size:
            break

        start += page_size
        time.sleep(1)  # beleefd pagineren

    return papers


def save_papers(all_papers: list):
    today = date.today().isoformat()
    fieldnames = ["fetch_date", "author_id", "name", "title", "year", "citations", "link"]

    # Overschrijf het bestand volledig bij elke run (snapshot)
    with open(OUTPUT_PAPERS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in all_papers:
            writer.writerow({"fetch_date": today, **p})

    print(f"✓ {len(all_papers)} papers opgeslagen in {OUTPUT_PAPERS_FILE}")


def print_citations_per_paper_year(all_papers: list):
    """Bereken en druk citaties/paper-jaar af per auteur."""
    current_year = date.today().year
    from collections import defaultdict
    stats = defaultdict(lambda: {"papers": 0, "total_cit": 0, "total_paper_years": 0})

    for p in all_papers:
        try:
            yr = int(p["year"])
        except (ValueError, TypeError):
            continue
        age = max(current_year - yr, 1)  # minimaal 1 jaar
        cit = int(p["citations"]) if p["citations"] else 0
        s = stats[p["name"]]
        s["papers"] += 1
        s["total_cit"] += cit
        s["total_paper_years"] += age

    print("\n── Citaties per paper-jaar ──────────────────────")
    for name, s in stats.items():
        if s["total_paper_years"] > 0:
            rate = s["total_cit"] / s["total_paper_years"]
            print(f"  {name}: {s['papers']} papers, "
                  f"{s['total_cit']} citaties, "
                  f"{s['total_paper_years']} paper-jaren → "
                  f"{rate:.2f} cit/paper-jaar")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--papers",
        action="store_true",
        help="Haal ook de volledige paperlijst op (trager, meer API calls)",
    )
    args = parser.parse_args()

    print("=" * 50)
    print(f"Citation Tracker — {date.today().isoformat()}")
    print("=" * 50)

    if SERPAPI_KEY == "JOUW_API_KEY_HIER":
        print("⚠ Stel SERPAPI_KEY in als environment variable!")
        return

    # ── Dagelijkse citatiefetch ──
    results = []
    for i, author in enumerate(AUTHORS):
        print(f"\nOpvragen citaties: {author['name']}...")
        results.append(get_citation_count(author))
        if i < len(AUTHORS) - 1:
            time.sleep(2)

    save_citations(results)

    # ── Paperlijst (optioneel) ──
    if args.papers:
        print("\n── Paperlijst ophalen ───────────────────────────")
        all_papers = []
        for i, author in enumerate(AUTHORS):
            print(f"\nPapers ophalen: {author['name']}...")
            papers = get_papers(author)
            all_papers.extend(papers)
            if i < len(AUTHORS) - 1:
                time.sleep(2)

        save_papers(all_papers)
        print_citations_per_paper_year(all_papers)

    print("\n" + "=" * 50)
    print("Klaar!")


if __name__ == "__main__":
    main()
