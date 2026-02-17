"""
Load processed documents from metadata into Neo4j
"""
import json
from pathlib import Path
from src.rag.graph import FinancialGraph

def load_all_documents():
    """Load all processed documents into Neo4j."""
    graph = FinancialGraph()
    metadata_dir = Path("data/processed/metadata")

    # Counters
    invoices_loaded = 0
    contracts_loaded = 0
    budgets_loaded = 0
    errors = []

    # Process all JSON files in metadata directory
    for json_file in metadata_dir.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                document = json.load(f)

            doc_type = document.get('document_type')

            if doc_type == 'invoice':
                graph.create_invoice_node(document)
                invoices_loaded += 1
                if invoices_loaded % 100 == 0:
                    print(f"  Loaded {invoices_loaded} invoices...")

            elif doc_type == 'contract':
                graph.create_contract_node(document)
                contracts_loaded += 1
                if contracts_loaded % 10 == 0:
                    print(f"  Loaded {contracts_loaded} contracts...")

            elif doc_type == 'budget':
                # Budgets are already loaded, skip
                budgets_loaded += 1

        except Exception as e:
            errors.append(f"{json_file.name}: {str(e)}")

    graph.close()

    # Print summary
    print("\n" + "="*60)
    print("NEO4J LOADING COMPLETE")
    print("="*60)
    print(f"Invoices loaded: {invoices_loaded}")
    print(f"Contracts loaded: {contracts_loaded}")
    print(f"Budgets (already loaded): {budgets_loaded}")

    if errors:
        print(f"\nErrors: {len(errors)}")
        for error in errors[:10]:  # Show first 10 errors
            print(f"  - {error}")
    else:
        print("\n[SUCCESS] All documents loaded successfully!")

if __name__ == "__main__":
    print("Loading processed documents into Neo4j...")
    load_all_documents()
