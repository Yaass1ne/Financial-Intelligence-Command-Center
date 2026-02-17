"""
FINCENTER Data Producer - Generates realistic, messy synthetic financial data

This script creates synthetic budgets, invoices, contracts, and accounting entries
with intentional imperfections to simulate real-world data quality issues.

Usage:
    python scripts/producer.py --output data/synthetic/ --num-invoices 500
"""

import argparse
import json
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from faker import Faker

# Initialize Faker for realistic data generation
fake = Faker(['fr_FR', 'en_US'])
Faker.seed(42)
random.seed(42)

# Financial constants
DEPARTMENTS = ["Marketing", "R&D", "IT", "Operations", "Sales", "HR", "Finance"]
EXPENSE_CATEGORIES = [
    "Frais généraux", "Consultants", "Logiciels", "Matériel", 
    "Déplacements", "Formation", "Marketing digital", "Salaires"
]
VENDORS = [
    "ACME Corp", "TechSolutions SA", "Global Services Ltd", "Innov'IT",
    "DataCorp", "CloudFirst SAS", "Consulting Partners", "Digital Agency"
]
CLIENTS = [
    "Entreprise Alpha", "Beta Industries", "Gamma Group", "Delta Corp",
    "Epsilon SA", "Zeta Solutions", "Eta Holdings"
]


class FinancialDataProducer:
    """Generates realistic, messy synthetic financial data."""
    
    def __init__(self, output_dir: Path, messiness_level: float = 0.3):
        """
        Args:
            output_dir: Root directory for synthetic data
            messiness_level: Probability of introducing errors (0.0 to 1.0)
        """
        self.output_dir = Path(output_dir)
        self.messiness = messiness_level
        
        # Create subdirectories
        (self.output_dir / "budgets").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "invoices").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "contracts").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "accounting").mkdir(parents=True, exist_ok=True)
        
    def _maybe_introduce_typo(self, text: str) -> str:
        """Randomly introduce typos to simulate real-world data."""
        if random.random() < self.messiness:
            if len(text) > 5:
                pos = random.randint(1, len(text) - 2)
                text = text[:pos] + random.choice(string.ascii_lowercase) + text[pos+1:]
        return text
    
    def _maybe_vary_date_format(self, date: datetime) -> str:
        """Return date in different formats to simulate inconsistency."""
        formats = [
            "%d/%m/%Y",      # European: 15/03/2024
            "%m/%d/%Y",      # American: 03/15/2024
            "%Y-%m-%d",      # ISO: 2024-03-15
            "%d.%m.%Y",      # Alternative: 15.03.2024
        ]
        
        if random.random() < self.messiness:
            return date.strftime(random.choice(formats))
        return date.strftime("%d/%m/%Y")  # Default European format
    
    def _maybe_vary_amount_format(self, amount: float) -> str:
        """Return amount in different formats."""
        formats = [
            lambda x: f"{x:,.2f}",        # 1,250.50
            lambda x: f"{x:.2f}".replace('.', ',').replace(',', '.', 1),  # 1.250,50
            lambda x: f"{x:.2f}",         # 1250.50
            lambda x: f"{x:,.2f} EUR",    # 1,250.50 EUR
        ]
        
        if random.random() < self.messiness:
            return random.choice(formats)(amount)
        return f"{amount:,.2f}"
    
    def generate_budgets(self, num_years: int = 3) -> List[str]:
        """Generate annual budget files with quarterly breakdowns."""
        budget_files = []
        
        for year in range(2022, 2022 + num_years):
            # Create budget structure
            budget_data = []
            
            for dept in DEPARTMENTS:
                for category in random.sample(EXPENSE_CATEGORIES, k=random.randint(3, 5)):
                    # Annual budget with quarterly breakdown
                    annual = random.randint(50000, 500000)
                    q1 = annual * random.uniform(0.20, 0.28)
                    q2 = annual * random.uniform(0.22, 0.30)
                    q3 = annual * random.uniform(0.20, 0.26)
                    q4 = annual - q1 - q2 - q3
                    
                    budget_data.append({
                        "Département": self._maybe_introduce_typo(dept),
                        "Catégorie": category,
                        "Budget Annuel": self._maybe_vary_amount_format(annual),
                        "Q1": self._maybe_vary_amount_format(q1),
                        "Q2": self._maybe_vary_amount_format(q2),
                        "Q3": self._maybe_vary_amount_format(q3),
                        "Q4": self._maybe_vary_amount_format(q4),
                    })
                    
                    # Sometimes duplicate rows (data quality issue)
                    if random.random() < self.messiness * 0.2:
                        budget_data.append(budget_data[-1].copy())
            
            # Save to Excel
            df = pd.DataFrame(budget_data)
            filename = self.output_dir / "budgets" / f"budget_{year}.xlsx"
            
            # Sometimes save with issues (merged cells, multiple sheets)
            if random.random() < self.messiness:
                # Create Excel with merged cells (harder to parse)
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=f"Budget {year}", index=False)
                    # Add a summary sheet
                    summary = df.groupby("Département")["Budget Annuel"].apply(
                        lambda x: x.str.replace(',', '').str.replace(' EUR', '').str.replace('EUR', '').astype(float).sum() if isinstance(x.iloc[0], str) else x.sum()
                    )
                    summary.to_excel(writer, sheet_name="Résumé")
            else:
                df.to_excel(filename, index=False)
            
            budget_files.append(str(filename))
            
        return budget_files
    
    def generate_invoices(self, num_invoices: int = 500) -> List[Dict[str, Any]]:
        """Generate invoice data (both JSON and later PDF)."""
        invoices = []
        
        start_date = datetime(2022, 1, 1)
        
        for i in range(num_invoices):
            invoice_date = start_date + timedelta(days=random.randint(0, 1095))
            due_date = invoice_date + timedelta(days=random.choice([15, 30, 45, 60]))
            
            # Generate invoice data
            invoice = {
                "invoice_id": f"INV-{invoice_date.year}-{i+1:04d}",
                "date": self._maybe_vary_date_format(invoice_date),
                "due_date": self._maybe_vary_date_format(due_date),
                "vendor": self._maybe_introduce_typo(random.choice(VENDORS)),
                "client": random.choice(CLIENTS),
                "items": [],
                "subtotal_ht": 0.0,
                "tax_rate": random.choice([0.20, 0.055]),  # TVA 20% or 5.5%
            }
            
            # Add line items
            num_items = random.randint(1, 5)
            for j in range(num_items):
                quantity = random.randint(1, 100)
                unit_price = random.uniform(10, 1000)
                total = quantity * unit_price
                
                item = {
                    "description": f"{random.choice(EXPENSE_CATEGORIES)} - Service {j+1}",
                    "quantity": quantity,
                    "unit_price": self._maybe_vary_amount_format(unit_price),
                    "total": self._maybe_vary_amount_format(total),
                }
                invoice["items"].append(item)
                invoice["subtotal_ht"] += total
            
            invoice["tax_amount"] = invoice["subtotal_ht"] * invoice["tax_rate"]
            invoice["total_ttc"] = invoice["subtotal_ht"] + invoice["tax_amount"]
            
            # Format final amounts
            invoice["subtotal_ht"] = self._maybe_vary_amount_format(invoice["subtotal_ht"])
            invoice["tax_amount"] = self._maybe_vary_amount_format(invoice["tax_amount"])
            invoice["total_ttc"] = self._maybe_vary_amount_format(invoice["total_ttc"])
            
            # Sometimes missing fields (data quality issue)
            if random.random() < self.messiness * 0.1:
                del invoice["due_date"]
            
            # Save as JSON
            filename = self.output_dir / "invoices" / f"{invoice['invoice_id']}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(invoice, f, indent=2, ensure_ascii=False)
            
            invoices.append(invoice)
        
        return invoices
    
    def generate_contracts(self, num_contracts: int = 50) -> List[Dict[str, Any]]:
        """Generate contract metadata (text content would be generated separately)."""
        contracts = []
        
        contract_types = ["Service Agreement", "Consulting", "License", "Maintenance"]
        
        for i in range(num_contracts):
            start_date = datetime(2022, 1, 1) + timedelta(days=random.randint(0, 730))
            duration_months = random.choice([12, 24, 36])
            end_date = start_date + timedelta(days=duration_months * 30)
            
            vendor = random.choice(VENDORS)
            client = random.choice(CLIENTS)

            contract = {
                "contract_id": f"CTR-{start_date.year}-{i+1:03d}",
                "type": random.choice(contract_types),
                "vendor": vendor,
                "client": client,
                "parties": [
                    {"name": vendor, "role": "Provider"},
                    {"name": client, "role": "Client"}
                ],
                "start_date": self._maybe_vary_date_format(start_date),
                "end_date": self._maybe_vary_date_format(end_date),
                "annual_value": random.randint(50000, 500000),
                "payment_terms": random.choice(["Net 30", "Net 45", "Net 60"]),
                "auto_renewal": random.choice([True, False]),
                "clauses": []
            }
            
            # Add random clauses
            possible_clauses = [
                {"type": "price_revision", "description": "Annual CPI adjustment"},
                {"type": "penalty", "description": "5% penalty per day of delay"},
                {"type": "termination", "description": "90 days notice required"},
                {"type": "exclusivity", "description": "Exclusive provider for 24 months"},
            ]
            
            contract["clauses"] = random.sample(possible_clauses, k=random.randint(1, 3))
            
            # Format amount
            contract["annual_value"] = self._maybe_vary_amount_format(contract["annual_value"])
            
            # Save as JSON
            filename = self.output_dir / "contracts" / f"{contract['contract_id']}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(contract, f, indent=2, ensure_ascii=False)
            
            contracts.append(contract)
        
        return contracts
    
    def generate_accounting_entries(self, num_entries: int = 1000) -> str:
        """Generate general ledger entries."""
        entries = []
        
        start_date = datetime(2022, 1, 1)
        
        accounts = {
            "601": "Achats stockés",
            "606": "Achats non stockés",
            "611": "Sous-traitance",
            "623": "Publicité",
            "641": "Rémunérations",
            "706": "Prestations de services",
        }
        
        for i in range(num_entries):
            entry_date = start_date + timedelta(days=random.randint(0, 1095))
            amount = random.uniform(100, 50000)
            
            entry = {
                "date": self._maybe_vary_date_format(entry_date),
                "account": random.choice(list(accounts.keys())),
                "account_name": accounts.get(random.choice(list(accounts.keys()))),
                "description": f"Transaction {i+1} - {random.choice(EXPENSE_CATEGORIES)}",
                "debit": self._maybe_vary_amount_format(amount) if random.random() > 0.5 else "",
                "credit": self._maybe_vary_amount_format(amount) if random.random() < 0.5 else "",
                "reference": f"JNL-{entry_date.year}-{i+1:05d}",
            }
            
            # Sometimes missing reference (data quality)
            if random.random() < self.messiness * 0.15:
                entry["reference"] = ""
            
            entries.append(entry)
        
        # Save as CSV
        df = pd.DataFrame(entries)
        filename = self.output_dir / "accounting" / "general_ledger.csv"
        df.to_csv(filename, index=False)
        
        return str(filename)
    
    def generate_all(self, num_invoices: int = 500, num_contracts: int = 50):
        """Generate complete synthetic dataset."""
        print("[FINCENTER] Data Producer - Starting generation...")
        print(f"[INFO] Messiness level: {self.messiness:.0%}")
        print()

        print("[1/4] Generating budgets...")
        budget_files = self.generate_budgets(num_years=3)
        print(f"   [OK] Created {len(budget_files)} budget files")

        print("[2/4] Generating invoices...")
        invoices = self.generate_invoices(num_invoices=num_invoices)
        print(f"   [OK] Created {len(invoices)} invoices")

        print("[3/4] Generating contracts...")
        contracts = self.generate_contracts(num_contracts=num_contracts)
        print(f"   [OK] Created {len(contracts)} contracts")

        print("[4/4] Generating accounting entries...")
        ledger_file = self.generate_accounting_entries(num_entries=1000)
        print(f"   [OK] Created general ledger: {ledger_file}")

        print()
        print("[SUCCESS] Data generation complete!")
        print(f"[OUTPUT] Directory: {self.output_dir}")
        print()
        print("[SUMMARY]")
        print(f"   - Budgets: {len(budget_files)}")
        print(f"   - Invoices: {len(invoices)}")
        print(f"   - Contracts: {len(contracts)}")
        print(f"   - Accounting entries: 1000")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic financial data for FINCENTER")
    parser.add_argument("--output", type=str, default="data/synthetic/",
                        help="Output directory for synthetic data")
    parser.add_argument("--num-invoices", type=int, default=500,
                        help="Number of invoices to generate")
    parser.add_argument("--num-contracts", type=int, default=50,
                        help="Number of contracts to generate")
    parser.add_argument("--messiness", type=float, default=0.3,
                        help="Data messiness level (0.0 to 1.0)")
    
    args = parser.parse_args()
    
    producer = FinancialDataProducer(
        output_dir=Path(args.output),
        messiness_level=args.messiness
    )
    
    producer.generate_all(
        num_invoices=args.num_invoices,
        num_contracts=args.num_contracts
    )


if __name__ == "__main__":
    main()
