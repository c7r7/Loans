import gradio as gr
from modules import data
import difflib

def compare_loans(file_a, file_b):
    """
    Compares two selected loan entries.
    Returns:
    1. Side-by-Side comparison text (Diff)
    2. Side-by-Side JSON comparison
    """
    if not file_a or not file_b:
        return "Please select two files to compare.", None, None
        
    entry_a = data.get_entry_by_filename(file_a)
    entry_b = data.get_entry_by_filename(file_b)
    
    if not entry_a or not entry_b:
        return "Error loading file data.", None, None
        
    # 1. Text Diff (using the raw extracted text? We didn't save raw text in DB, only JSON)
    # Using JSON dump for diff is cleaner for structured data
    
    json_str_a = str(entry_a.get("full_json", {}))
    json_str_b = str(entry_b.get("full_json", {}))
    
    # Simple diff report
    report = f"### Comparison Report\n"
    report += f"**File A**: {file_a} (Borrower: {entry_a['borrower']})\n"
    report += f"**File B**: {file_b} (Borrower: {entry_b['borrower']})\n\n"
    
    # Highlight specific changes in key fields
    changes = []
    keys_to_compare = ["amount", "interest", "maturity", "lender"]
    for k in keys_to_compare:
        val_a = entry_a.get(k, "N/A")
        val_b = entry_b.get(k, "N/A")
        if val_a != val_b:
            changes.append(f"- **{k.title()}**: '{val_a}'  ➡️  '{val_b}'")
            
    if changes:
        report += "#### Key Differences:\n" + "\n".join(changes)
    else:
        report += "#### Key fields are identical."
        
    return report, entry_a["full_json"], entry_b["full_json"]


def create_tab():
    with gr.Column():
        gr.Markdown("### ⚖️ Loan Agreement Comparison")
        gr.Markdown("Select two documents to compare their extract terms and identify changes (e.g., amendments).")
        
        with gr.Row():
            dropdown_a = gr.Dropdown(label="Document A (Original)", choices=[], interactive=True)
            dropdown_b = gr.Dropdown(label="Document B (Amended/New)", choices=[], interactive=True)
        
        compare_btn = gr.Button("Compare Documents", variant="primary")
        
        # Refresh dropdowns button (since list changes dynamically)
        refresh_options_btn = gr.Button("🔄 Refresh Document List", size="sm")

        gr.Markdown("---")
        
        # Results
        comparison_report = gr.Markdown(label="Analysis")
        
        with gr.Row():
            json_a_view = gr.JSON(label="Document A Data")
            json_b_view = gr.JSON(label="Document B Data")

        # --- Logic ---
        
        def update_choices():
            opts = data.get_file_options()
            return gr.Dropdown(choices=opts), gr.Dropdown(choices=opts)
            
        refresh_options_btn.click(
            fn=update_choices, 
            inputs=[], 
            outputs=[dropdown_a, dropdown_b]
        )
        
        compare_btn.click(
            fn=compare_loans,
            inputs=[dropdown_a, dropdown_b],
            outputs=[comparison_report, json_a_view, json_b_view]
        )
        
        # Auto-refresh choices on load (doesn't always work perfectly in Gradio modular builds, manual refresh button provided)
        
        return {
            "dropdown_a": dropdown_a, 
            "dropdown_b": dropdown_b
        }
