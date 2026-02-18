"""
Fetch real contract data from SEC EDGAR EX-10 filings (2024-2025)
and/or from the CUAD dataset CSV annotations, then ingest into Neo4j.

Usage:
  # Fetch 25 contracts from SEC EDGAR (default)
  python scripts/fetch_real_contracts.py

  # Fetch 40 contracts from EDGAR only
  python scripts/fetch_real_contracts.py --source edgar --limit 40

  # Load CUAD annotations from local CSV (after downloading from Zenodo)
  python scripts/fetch_real_contracts.py --source cuad --cuad-csv path/to/CUAD_v1.csv

  # Both sources
  python scripts/fetch_real_contracts.py --source both --limit 20 --cuad-csv path/to/CUAD_v1.csv

CUAD dataset download:
  curl -L https://zenodo.org/records/4595826/files/CUAD_v1.zip -o CUAD_v1.zip
  unzip CUAD_v1.zip
  Then pass --cuad-csv CUAD_v1/CUAD_v1.csv

SEC EDGAR:
  Queries the free EDGAR full-text search (no API key required).
  User-Agent header is mandatory per EDGAR ToS.
"""

import re
import sys
import time
import argparse
import json
import csv
from pathlib import Path
from datetime import datetime, timedelta

# ── bootstrap sys.path so src.* imports work ──────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.graph import FinancialGraph

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("[WARN] requests not installed. Run: pip install requests")

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

# SEC EDGAR requires a User-Agent with contact info (their ToS)
EDGAR_HEADERS = {
    "User-Agent": "F360-Research contact@f360.ai",
    "Accept": "application/json",
}

EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_DOC_BASE   = "https://www.sec.gov"

# Rate limit: EDGAR allows 10 requests/second max
EDGAR_DELAY = 0.15  # seconds between requests

# Contract types we want to detect
CONTRACT_KEYWORDS = [
    '"service agreement"',
    '"consulting agreement"',
    '"supply agreement"',
    '"software license agreement"',
    '"master services agreement"',
    '"professional services agreement"',
]

# ─────────────────────────────────────────────────────────────────────────────
# Shared parsing helpers (same logic as ingest_contracts.py)
# ─────────────────────────────────────────────────────────────────────────────

MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}


def norm_date(s: str) -> str:
    """Normalize any date string to YYYY-MM-DD."""
    s = s.strip()
    # Already YYYY-MM-DD
    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        return s
    # DD/MM/YYYY or MM/DD/YYYY
    m = re.match(r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})$", s)
    if m:
        a, b, y = m.groups()
        y = "20" + y if len(y) == 2 else y
        # Assume MM/DD/YYYY for US contracts from EDGAR
        return f"{y}-{a.zfill(2)}-{b.zfill(2)}"
    # Month DD, YYYY  or  DD Month YYYY
    m2 = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})", s)
    if m2:
        mn, day, yr = m2.groups()
        mo_num = MONTHS.get(mn.lower(), "01")
        return f"{yr}-{mo_num}-{day.zfill(2)}"
    m3 = re.match(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", s)
    if m3:
        day, mn, yr = m3.groups()
        mo_num = MONTHS.get(mn.lower(), "01")
        return f"{yr}-{mo_num}-{day.zfill(2)}"
    return "2026-12-31"  # fallback


def parse_contract_text(text: str, contract_id: str) -> dict:
    """Extract contract fields from raw text using regex heuristics."""

    def find(patterns, default="UNKNOWN"):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return default

    # Vendor / counterparty name
    vendor = find([
        r"(?:between|party\s*[:\-]\s*(?:one|1|a|\"[^\"]*\"))[,\s]+([A-Z][A-Za-z &,\.]+(?:Inc|LLC|Corp|Ltd|LP|LLP|Co)[\.']?)",
        r"(?:LENDER|supplier|service\s*provider|vendor|contractor)\s*[:\-]\s*([A-Z][A-Za-z &,\.]{3,60})",
        r"(?:company|firm|corporation)\s+known\s+as\s+([A-Z][A-Za-z &,\.]{3,60})",
        r"(?:entered into by|agreement\s+by)\s+(?:and\s+between\s+)?([A-Z][A-Za-z &,\.]+(?:Inc|LLC|Corp|Ltd|LP)[\.']?)",
    ])
    # Clean up vendor if it captured too much
    if vendor != "UNKNOWN" and len(vendor) > 60:
        vendor = vendor[:60].rstrip(" ,.")

    # Effective / start date
    start_raw = find([
        r"effective(?:\s+as\s+of)?\s+(?:date[:\s]+)?([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"effective(?:\s+as\s+of)?\s+(?:date[:\s]+)?(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"(?:start|commencement)\s+date[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"(?:start|commencement)\s+date[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"dated(?:\s+as\s+of)?\s+([A-Za-z]+ \d{1,2},?\s*\d{4})",
    ], "2024-01-01")

    # End / termination date
    end_raw = find([
        r"(?:termination|expir(?:ation|y)|end)\s+date[:\s]+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"(?:termination|expir(?:ation|y)|end)\s+date[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"(?:expires?|terminates?)\s+on\s+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"(?:initial\s+term|term\s+of).*?(?:ending|until|through)\s+([A-Za-z]+ \d{1,2},?\s*\d{4})",
        r"through\s+([A-Za-z]+ \d{1,2},?\s*\d{4})",
    ], "2026-12-31")

    # Contract value
    value_str = find([
        r"(?:total|aggregate|contract|annual|maximum)\s+(?:contract\s+)?(?:value|amount|fee|consideration)[:\s]+[\$€£]?\s*([\d,\.]+)",
        r"[\$€£]\s*([\d,\.]+)\s*(?:per\s*(?:year|annum|month)|annually|\/yr|\/year)",
        r"(?:fee|payment|compensation)\s+of\s+[\$€£]?\s*([\d,\.]+)",
        r"FINANCED\s+AMOUNT[:\s]+[\$€£]?\s*([\d,\.]+)",
        r"[\$€£]([\d,]+(?:\.\d+)?)\s*(?:million|thousand)?",
    ], "0")
    # Handle "million" / "thousand" multipliers
    value_mult = 1.0
    mult_m = re.search(r"[\$€£]([\d,\.]+)\s*(million|thousand)", text, re.IGNORECASE)
    if mult_m:
        value_str = mult_m.group(1)
        value_mult = 1_000_000 if mult_m.group(2).lower() == "million" else 1_000
    try:
        annual_value = float(value_str.replace(",", "").replace(" ", "").rstrip(".")) * value_mult
    except ValueError:
        annual_value = 0.0

    # Contract type
    contract_type = "SERVICE"
    if re.search(r"license|licensing|software|saas|subscription", text, re.IGNORECASE):
        contract_type = "LICENSE"
    elif re.search(r"consulting|advisory|professional\s+services", text, re.IGNORECASE):
        contract_type = "CONSULTING"
    elif re.search(r"supply|procurement|purchase|vendor|delivery", text, re.IGNORECASE):
        contract_type = "SUPPLY"
    elif re.search(r"lease|rental|property", text, re.IGNORECASE):
        contract_type = "LEASE"
    elif re.search(r"employment|executive|compensation|severance", text, re.IGNORECASE):
        contract_type = "EMPLOYMENT"

    return {
        "id": contract_id,
        "contract_id": contract_id,
        "type": contract_type,
        "vendor": vendor if vendor != "UNKNOWN" else "Unknown Vendor",
        "start_date": norm_date(start_raw),
        "end_date": norm_date(end_raw),
        "annual_value": annual_value,
        "auto_renewal": bool(re.search(r"auto.?renew|automatic.?renewal|automatically\s+renew", text, re.IGNORECASE)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SEC EDGAR fetcher
# ─────────────────────────────────────────────────────────────────────────────

def search_edgar(query: str, limit: int = 10, start_date: str = "2024-01-01") -> list:
    """Search EDGAR full-text search and return hits with EX-10 file types."""
    if not HAS_REQUESTS:
        return []
    params = {
        "q": query,
        "dateRange": "custom",
        "startdt": start_date,
        "enddt": datetime.now().strftime("%Y-%m-%d"),
    }
    try:
        resp = requests.get(EDGAR_SEARCH_URL, params=params, headers=EDGAR_HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        all_hits = data.get("hits", {}).get("hits", [])
        # Filter for EX-10 exhibit types only
        ex10_hits = [
            h for h in all_hits
            if re.match(r"EX-10", h.get("_source", {}).get("file_type", ""), re.IGNORECASE)
        ]
        return ex10_hits[:limit]
    except Exception as e:
        print(f"  [WARN] EDGAR search failed for '{query}': {e}")
        return []


def fetch_exhibit_text(cik: str, adsh: str, file_type: str) -> str:
    """
    Given a CIK and accession number, find the EX-10 exhibit file in the
    filing directory and return its plain text (HTML stripped).
    """
    if not HAS_REQUESTS:
        return ""
    cik_clean  = str(int(cik))           # strip leading zeros
    adsh_clean = adsh.replace("-", "")   # 0001234567-24-000001 → 000123456724000001
    dir_url    = f"{EDGAR_DOC_BASE}/Archives/edgar/data/{cik_clean}/{adsh_clean}/"
    try:
        time.sleep(EDGAR_DELAY)
        resp = requests.get(dir_url, headers=EDGAR_HEADERS, timeout=15)
        if not resp.ok:
            return ""
        # Find exhibit files: ex10*.htm, exhibit10*.htm, etc.
        files = re.findall(
            r'href="(/Archives/edgar/data/[^"]+\.(?:htm|txt))"',
            resp.text, re.IGNORECASE
        )
        # Prefer files with "ex10" or "ex-10" in the name
        exhibit_files = [
            f for f in files
            if re.search(r"ex.?10|exhibit.?10", f, re.IGNORECASE)
        ]
        if not exhibit_files:
            # Fall back: pick any .htm that isn't the index or main form
            exhibit_files = [
                f for f in files
                if not re.search(r"index|10-[kq]|def14|8-k", f, re.IGNORECASE)
            ]
        if not exhibit_files:
            return ""
        # Download the first matching exhibit
        doc_url = EDGAR_DOC_BASE + exhibit_files[0]
        time.sleep(EDGAR_DELAY)
        doc_resp = requests.get(doc_url, headers=EDGAR_HEADERS, timeout=30)
        if not doc_resp.ok:
            return ""
        text = doc_resp.text
        # Strip HTML
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&#\d+;", " ", text)
        text = re.sub(r"\s{3,}", "\n", text)
        return text[:50000]
    except Exception as e:
        print(f"  [WARN] Exhibit fetch failed ({cik}/{adsh}): {e}")
        return ""


def fetch_edgar_contracts(limit: int = 25, start_date: str = "2024-01-01") -> list[dict]:
    """Fetch and parse real contracts from SEC EDGAR EX-10 filings."""
    print(f"\n[EDGAR] Searching for {limit} EX-10 contracts filed since {start_date}...")
    all_hits: list = []

    # Spread across multiple keyword queries for variety
    per_query = max(2, (limit * 2) // len(CONTRACT_KEYWORDS))
    for kw in CONTRACT_KEYWORDS:
        hits = search_edgar(kw, per_query, start_date)
        all_hits.extend(hits)
        time.sleep(EDGAR_DELAY)
        if len(all_hits) >= limit * 3:
            break

    # Deduplicate by accession number (adsh)
    seen: set = set()
    unique_hits: list = []
    for h in all_hits:
        adsh = h.get("_source", {}).get("adsh", h.get("_id", ""))
        if adsh and adsh not in seen:
            seen.add(adsh)
            unique_hits.append(h)

    print(f"[EDGAR] {len(unique_hits)} unique EX-10 filings found, downloading up to {limit}...")

    contracts: list[dict] = []
    counter = 1

    for hit in unique_hits:
        if counter > limit:
            break
        src         = hit.get("_source", {})
        display     = src.get("display_names", ["Unknown Corp"])[0]
        entity_name = re.sub(r"\s*\(CIK[^\)]+\)", "", display).strip()
        file_date   = src.get("file_date", "2024-01-01")
        adsh        = src.get("adsh", "")
        file_type   = src.get("file_type", "EX-10")
        ciks        = src.get("ciks", [])

        if not adsh or not ciks:
            continue

        cik = ciks[0]
        print(f"  [{counter:02d}] {entity_name[:45]:<45} {file_date}  [{file_type}]")

        text = fetch_exhibit_text(cik, adsh, file_type)

        if len(text) < 300:
            print(f"       [SKIP] Exhibit too short ({len(text)} chars)")
            continue

        contract_id = f"CTR-SEC-{counter:03d}"
        data = parse_contract_text(text, contract_id)

        # Override vendor with EDGAR filer name if regex didn't find one
        if data["vendor"] == "Unknown Vendor" and entity_name:
            data["vendor"] = entity_name[:80]

        # Use filing date as start_date when text didn't yield one
        if data["start_date"] == "2024-01-01" and file_date and file_date != "2024-01-01":
            data["start_date"] = norm_date(file_date)

        contracts.append(data)
        counter += 1

    print(f"[EDGAR] Parsed {len(contracts)} contracts successfully")
    return contracts


# ─────────────────────────────────────────────────────────────────────────────
# CUAD Dataset loader
# ─────────────────────────────────────────────────────────────────────────────

# CUAD CSV column mappings (CUAD_v1.csv has QA annotation format)
# The master CSV has: Filename, Question, Answer columns
CUAD_QUESTION_MAP = {
    "Parties": "vendor",
    "Agreement Date": "start_date",
    "Expiration Date": "end_date",
    "Contract Value": "annual_value",
    "Auto-Renewal": "auto_renewal",
    "Contract Type": "type",
}


def load_cuad_csv(csv_path: str, limit: int = 50) -> list[dict]:
    """
    Load contract metadata from CUAD v1 CSV annotations.

    CUAD CSV format (from Zenodo):
      Filename, Question, Answer, ...
    or the squad-format JSON which has a different structure.

    Handles both the flat CSV and the QA-style annotation format.
    """
    print(f"\n[CUAD] Loading annotations from {csv_path}...")
    path = Path(csv_path)
    if not path.exists():
        print(f"[CUAD] File not found: {csv_path}")
        return []

    # Try to auto-detect format
    with open(csv_path, encoding="utf-8", errors="replace") as f:
        sample = f.read(2000)

    # Format 1: Flat CSV with columns Filename, Question, Answer
    if "Question" in sample and "Answer" in sample:
        return _load_cuad_qa_csv(csv_path, limit)

    # Format 2: CUAD master CSV (Filename, Category, ...)
    return _load_cuad_master_csv(csv_path, limit)


def _load_cuad_qa_csv(csv_path: str, limit: int) -> list[dict]:
    """Load CUAD QA-format CSV where each row is (Filename, Question, Answer)."""
    by_file: dict[str, dict] = {}

    with open(csv_path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fname = row.get("Filename", row.get("filename", "")).strip()
            question = row.get("Question", row.get("question", "")).strip()
            answer = row.get("Answer", row.get("answer", "")).strip()
            if not fname or not answer or answer.lower() in ("", "n/a", "none", "not mentioned"):
                continue
            if fname not in by_file:
                by_file[fname] = {"_filename": fname}
            # Map known questions to fields
            for q_key, field in CUAD_QUESTION_MAP.items():
                if q_key.lower() in question.lower():
                    by_file[fname][field] = answer

    contracts = []
    for i, (fname, fields) in enumerate(list(by_file.items())[:limit]):
        contract_id = f"CTR-CUAD-{i+1:03d}"
        vendor = fields.get("vendor", "UNKNOWN")
        # CUAD "Parties" answer often lists both parties — take first
        if vendor != "UNKNOWN" and ";" in vendor:
            vendor = vendor.split(";")[0].strip()
        if vendor != "UNKNOWN" and "\n" in vendor:
            vendor = vendor.split("\n")[0].strip()

        start_raw = fields.get("start_date", "2024-01-01")
        end_raw   = fields.get("end_date", "2026-12-31")
        val_raw   = fields.get("annual_value", "0")
        auto_renew_raw = fields.get("auto_renewal", "No")

        try:
            annual_value = float(re.sub(r"[^\d\.]", "", val_raw or "0") or "0")
        except ValueError:
            annual_value = 0.0

        contracts.append({
            "id": contract_id,
            "contract_id": contract_id,
            "type": fields.get("type", "SERVICE"),
            "vendor": vendor if vendor != "UNKNOWN" else f"Vendor-CUAD-{i+1}",
            "start_date": norm_date(start_raw),
            "end_date": norm_date(end_raw),
            "annual_value": annual_value,
            "auto_renewal": "yes" in str(auto_renew_raw).lower(),
        })

    print(f"[CUAD] Loaded {len(contracts)} contracts from {len(by_file)} files")
    return contracts


def _load_cuad_master_csv(csv_path: str, limit: int) -> list[dict]:
    """Fallback: treat CSV as tabular data with one row per contract."""
    contracts = []
    with open(csv_path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            # Try common column names
            vendor = (row.get("Party Name") or row.get("Vendor") or
                      row.get("Company") or row.get("Name") or f"Vendor-CUAD-{i+1}")
            start  = (row.get("Effective Date") or row.get("Start Date") or
                      row.get("Agreement Date") or "2024-01-01")
            end    = (row.get("Expiration Date") or row.get("End Date") or
                      row.get("Termination Date") or "2026-12-31")
            value  = (row.get("Contract Value") or row.get("Annual Value") or
                      row.get("Amount") or "0")
            try:
                annual_value = float(re.sub(r"[^\d\.]", "", value or "0") or "0")
            except ValueError:
                annual_value = 0.0

            contract_id = f"CTR-CUAD-{i+1:03d}"
            contracts.append({
                "id": contract_id,
                "contract_id": contract_id,
                "type": "SERVICE",
                "vendor": str(vendor).strip()[:80],
                "start_date": norm_date(str(start)),
                "end_date": norm_date(str(end)),
                "annual_value": annual_value,
                "auto_renewal": False,
            })

    print(f"[CUAD] Loaded {len(contracts)} contracts (tabular mode)")
    return contracts


# ─────────────────────────────────────────────────────────────────────────────
# Neo4j ingestion
# ─────────────────────────────────────────────────────────────────────────────

def ingest_contracts(contracts: list[dict], graph: FinancialGraph, dry_run: bool = False):
    """Store parsed contracts in Neo4j, then link to matching invoices."""
    ok = skipped = 0

    for data in contracts:
        if dry_run:
            print(f"  [DRY] {data['contract_id']} | {data['vendor'][:40]} | "
                  f"{data['start_date']} -> {data['end_date']} | {data['annual_value']:,.0f} EUR")
            ok += 1
            continue
        try:
            graph.create_contract(data)
            print(f"  [OK]  {data['contract_id']} | {data['vendor'][:40]:<40} | "
                  f"{data['end_date']} | {data['annual_value']:>10,.0f} EUR")
            ok += 1
        except Exception as e:
            print(f"  [ERR] {data['contract_id']}: {e}")
            skipped += 1

    return ok, skipped


def link_contracts_to_invoices(graph: FinancialGraph):
    """Create GENERATES relationships between new contracts and matching invoices."""
    print("\n[LINK] Creating Contract->Invoice relationships by vendor name match...")
    try:
        with graph.driver.session() as session:
            result = session.run("""
                MATCH (c:Contract), (i:Invoice)
                WHERE toLower(trim(i.vendor)) = toLower(trim(c.vendor))
                  AND NOT (c)-[:GENERATES]->(i)
                MERGE (c)-[:GENERATES]->(i)
                RETURN count(*) AS created
            """)
            rec = result.single()
            n = rec["created"] if rec else 0
            print(f"[LINK] Created {n} new Contract->Invoice relationships")
    except Exception as e:
        print(f"[LINK] Warning: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch real contracts from SEC EDGAR and/or CUAD into Neo4j"
    )
    parser.add_argument(
        "--source", choices=["edgar", "cuad", "both"], default="edgar",
        help="Data source to use (default: edgar)"
    )
    parser.add_argument(
        "--limit", type=int, default=25,
        help="Max contracts to fetch from EDGAR (default: 25)"
    )
    parser.add_argument(
        "--start-date", default="2024-01-01",
        help="Earliest filing date for EDGAR search (default: 2024-01-01)"
    )
    parser.add_argument(
        "--cuad-csv", default="",
        help="Path to CUAD_v1.csv annotation file (required for --source cuad|both)"
    )
    parser.add_argument(
        "--cuad-limit", type=int, default=50,
        help="Max contracts to load from CUAD CSV (default: 50)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and print contracts without writing to Neo4j"
    )
    args = parser.parse_args()

    if not HAS_REQUESTS and args.source in ("edgar", "both"):
        print("[ERROR] 'requests' package required for EDGAR. Install: pip install requests")
        sys.exit(1)

    all_contracts: list[dict] = []

    # ── SEC EDGAR ──────────────────────────────────────────────────────────────
    if args.source in ("edgar", "both"):
        edgar_contracts = fetch_edgar_contracts(
            limit=args.limit,
            start_date=args.start_date,
        )
        all_contracts.extend(edgar_contracts)

    # ── CUAD ──────────────────────────────────────────────────────────────────
    if args.source in ("cuad", "both"):
        if not args.cuad_csv:
            print("[ERROR] --cuad-csv is required when --source includes cuad")
            print("  Download: https://zenodo.org/records/4595826/files/CUAD_v1.zip")
            sys.exit(1)
        cuad_contracts = load_cuad_csv(args.cuad_csv, limit=args.cuad_limit)
        # Re-number CUAD IDs to avoid collision with EDGAR ones
        offset = len(all_contracts)
        for i, c in enumerate(cuad_contracts):
            c["id"] = f"CTR-CUAD-{offset + i + 1:03d}"
            c["contract_id"] = c["id"]
        all_contracts.extend(cuad_contracts)

    if not all_contracts:
        print("\n[DONE] No contracts fetched. Check network connectivity or CSV path.")
        return

    print(f"\n[INFO] Total contracts to ingest: {len(all_contracts)}")

    # ── Neo4j ingestion ────────────────────────────────────────────────────────
    if args.dry_run:
        print("\n[DRY RUN] Showing parsed contracts (not writing to Neo4j):\n")
        graph = None
        ok, skipped = ingest_contracts(all_contracts, None, dry_run=True)  # type: ignore
    else:
        graph = FinancialGraph()
        ok, skipped = ingest_contracts(all_contracts, graph)
        link_contracts_to_invoices(graph)
        graph.close()

    print(f"\n[DONE] Ingested {ok} contracts, {skipped} errors.")
    if skipped > 0:
        print(f"  Tip: Run with --dry-run to preview parsed fields before ingesting.")


if __name__ == "__main__":
    main()
