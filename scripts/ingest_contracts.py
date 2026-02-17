# Ingest the 30 English contract PDFs into the FINCENTER graph.
# Usage: python scripts/ingest_contracts.py --dir "C:/Users/Yassine/Desktop/Contracts_30_English"

import re
import argparse
import uuid
from pathlib import Path

# ── bootstrap sys.path so src.* imports work ──────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.graph import FinancialGraph

try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    print("[WARN] pdfplumber not installed – text extraction will be skipped")


# ─────────────────────────────────────────────────────────────────────────────
# Extraction helpers
# ─────────────────────────────────────────────────────────────────────────────

def extract_text(pdf_path: Path) -> str:
    if not HAS_PDF:
        return ""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages[:6])
    except Exception as e:
        print(f"  [WARN] Could not read {pdf_path.name}: {e}")
        return ""


def parse_contract(text: str, filename: str) -> dict:
    """Extract key fields from contract text using regex heuristics."""

    def find(patterns, default="UNKNOWN"):
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return default

    # Contract ID from filename (Contract_1.pdf → CTR-ENG-001)
    num_m = re.search(r"(\d+)", filename)
    num = num_m.group(1).zfill(3) if num_m else uuid.uuid4().hex[:6]
    contract_id = f"CTR-ENG-{num}"

    # Vendor / Party names
    vendor = find([
        r"(?:between|party\s*1|vendor|supplier|service\s*provider)[:\s]+([A-Z][^\n,]{3,50})",
        r"(?:company|firm|corporation)[:\s]+([A-Z][^\n,]{3,50})",
    ])

    # Dates
    start_date = find([
        r"(?:effective\s*date|start\s*date|commencement)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"(?:effective\s*date|start\s*date)[:\s]+(\w+ \d{1,2},?\s*\d{4})",
    ], "2025-01-01")

    end_date = find([
        r"(?:termination\s*date|end\s*date|expiry)[:\s]+(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"(?:expir(?:es?|ation))[:\s]+(\w+ \d{1,2},?\s*\d{4})",
    ], "2026-12-31")

    # Value
    value_str = find([
        r"(?:total\s*value|contract\s*value|annual\s*value|amount)[:\s]+[\$€£]?\s*([\d,\.]+)",
        r"[\$€£]\s*([\d,\.]+)\s*(?:per\s*year|annually|\/yr)",
    ], "0")
    try:
        annual_value = float(value_str.replace(",", "").replace(" ", ""))
    except ValueError:
        annual_value = 0.0

    # Normalize dates to YYYY-MM-DD
    def norm_date(s: str) -> str:
        s = s.strip()
        # DD/MM/YYYY or MM/DD/YYYY
        m = re.match(r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})$", s)
        if m:
            d, mo, y = m.groups()
            y = "20" + y if len(y) == 2 else y
            return f"{y}-{mo.zfill(2)}-{d.zfill(2)}"
        # Month DD YYYY
        months = {"january":"01","february":"02","march":"03","april":"04","may":"05",
                  "june":"06","july":"07","august":"08","september":"09","october":"10",
                  "november":"11","december":"12"}
        m2 = re.match(r"(\w+)\s+(\d{1,2}),?\s*(\d{4})", s, re.IGNORECASE)
        if m2:
            mn, day, yr = m2.groups()
            mo_num = months.get(mn.lower(), "01")
            return f"{yr}-{mo_num}-{day.zfill(2)}"
        return s if re.match(r"\d{4}-\d{2}-\d{2}", s) else "2026-12-31"

    return {
        "id": contract_id,
        "contract_id": contract_id,
        "type": "SERVICE",
        "vendor": vendor,
        "start_date": norm_date(start_date),
        "end_date": norm_date(end_date),
        "annual_value": annual_value,
        "auto_renewal": bool(re.search(r"auto.?renew", text, re.IGNORECASE)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=r"C:/Users/Yassine/Desktop/Contracts_30_English")
    args = parser.parse_args()

    folder = Path(args.dir)
    pdfs = sorted(folder.glob("*.pdf"))
    print(f"[INFO] Found {len(pdfs)} PDF contracts in {folder}")

    graph = FinancialGraph()
    ok = skipped = 0

    for pdf in pdfs:
        text = extract_text(pdf)
        data = parse_contract(text, pdf.name)
        try:
            graph.create_contract(data)
            print(f"  [OK]  {pdf.name} -> {data['contract_id']} | vendor={data['vendor'][:40]} | end={data['end_date']}")
            ok += 1
        except Exception as e:
            print(f"  [ERR] {pdf.name}: {e}")
            skipped += 1

    graph.close()
    print(f"\n[DONE] Ingested {ok} contracts, {skipped} errors.")


if __name__ == "__main__":
    main()
