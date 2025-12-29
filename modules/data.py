import json
import os
import logging

# File to persist data
DB_FILE = "loan_database.json"

def load_database():
    """Lengths the database from disk if exists."""
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_database():
    """Saves the database to disk."""
    with open(DB_FILE, "w") as f:
        json.dump(LOAN_DATABASE, f, indent=2)

# Initialize in-memory storage from disk
LOAN_DATABASE = load_database()

def add_loan(filename, filepath, json_data):
    """
    Registers a new loan into the database and persists it.
    """
    # Extract data handling nested 'core_loan_terms' if present
    data = json_data
    if isinstance(json_data, dict) and "core_loan_terms" in json_data:
        data = json_data["core_loan_terms"]
        
    # Safely get fields
    def get_field(keys, default="N/A"):
        # Helper to try multiple keys or return default
        for k in keys:
            if data.get(k): return data[k]
        return default

    borrower = get_field(["borrower"], "Unknown")
    lender = get_field(["lenders", "administrative_agent"], "Unknown") # specific user request for Lender
    
    amount_val = get_field(["loan_amount"], "")
    currency = get_field(["currency"], "")
    amount = f"{amount_val} {currency}".strip() if amount_val else "N/A"
    
    # Construct Interest Rate string
    # e.g. "Floating SOFR + 2.5%"
    int_type = get_field(["interest_type"], "")
    bench = get_field(["benchmark_rate"], "")
    margin = data.get("margin", {})
    margin_str = ""
    if isinstance(margin, dict):
        m_min = margin.get("min")
        m_max = margin.get("max")
        if m_min and m_max: margin_str = f"{m_min}-{m_max}%"
        elif m_min: margin_str = f"{m_min}%"
    
    interest = f"{int_type} {bench} {margin_str}".strip() or "N/A"
    
    maturity = get_field(["maturity_or_termination_date"], "N/A")

    entry = {
        "filename": filename,
        "filepath": filepath,
        "borrower": borrower,
        "lender": lender,
        "amount": amount,
        "interest": interest,
        "maturity": maturity,
        "full_json": json_data
    }
    
    # Check for duplicates (by filename) and update if exists, or append
    existing_idx = next((i for i, x in enumerate(LOAN_DATABASE) if x["filename"] == filename), None)
    if existing_idx is not None:
        LOAN_DATABASE[existing_idx] = entry
    else:
        LOAN_DATABASE.append(entry)
        
    save_database()
    return entry

def get_dataframe_data(query=None):
    """
    Returns data formatted for the Gradio Dataframe.
    Columns: [Filename, Borrower, Lender, Amount, Interest, Maturity, Actions...]
    Supports filtering by query string.
    """
    rows = []
    for entry in LOAN_DATABASE:
        # Filter logic
        if query:
            q = query.lower()
            # Search across all visible fields
            values = [
                entry["filename"], 
                entry["borrower"], 
                entry["lender"], 
                entry["amount"], 
                entry["interest"], 
                entry["maturity"]
            ]
            if not any(q in str(v).lower() for v in values):
                continue

        rows.append([
            entry["filename"],
            entry["borrower"],
            entry["lender"],
            entry["amount"],
            entry["interest"],
            entry["maturity"],
            "📄 View PDF",   
            "🔍 View JSON"   
        ])
    return rows

def get_file_options():
    """Returns a list of filenames for dropdowns."""
    return [x["filename"] for x in LOAN_DATABASE]

def get_entry_by_filename(filename):
    return next((x for x in LOAN_DATABASE if x["filename"] == filename), None)
