import gradio as gr
from modules import data
import difflib
import json

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
    
    json_a = entry_a.get("full_json", {})
    json_b = entry_b.get("full_json", {})
    
    # Convert to formatted strings for diff
    a_lines = json.dumps(json_a, indent=2, sort_keys=True).splitlines()
    b_lines = json.dumps(json_b, indent=2, sort_keys=True).splitlines()
    
    # Generate HTML Diff
    differ = difflib.HtmlDiff()
    # We add some custom CSS to make it look nicer in the app
    diff_html = differ.make_table(a_lines, b_lines, fromdesc=file_a, todesc=file_b, context=True, numlines=5)
    
    # Add styling with !important to override dark mode defaults
    style = """
    <style>
    .diff { font-family: 'Consolas', 'Monaco', 'Andale Mono', monospace !important; font-size: 13px !important; width: 100% !important; border-collapse: collapse !important; background: white !important; border: 1px solid #ddd !important; }
    .diff td { padding: 4px 8px !important; border: 1px solid #eee !important; vertical-align: top !important; white-space: pre-wrap !important; word-break: break-word !important; color: #333 !important; background-color: white; }
    .diff_header { background-color: #f8f9fa !important; color: #666 !important; font-weight: bold !important; text-align: right !important; width: 1% !important; border-right: 1px solid #ccc !important; }
    .diff_next { display: none !important; }
    .diff_add { background-color: #e6ffec !important; color: #24292e !important; }
    .diff_chg { background-color: #fffbdd !important; color: #24292e !important; }
    .diff_sub { background-color: #ffebe9 !important; color: #24292e !important; }
    </style>
    """
    final_html = style + "<div style='overflow-x:auto; background-color: white !important; color: #333 !important; padding: 10px; border-radius: 4px;'>" + diff_html + "</div>"
    
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
        
    return report, final_html


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
        
        gr.Markdown("#### Detailed JSON Diff")
        diff_view = gr.HTML(label="Side-by-Side Comparison")

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
            outputs=[comparison_report, diff_view]
        )
        
        # Auto-refresh choices on load (doesn't always work perfectly in Gradio modular builds, manual refresh button provided)
        
        return {
            "dropdown_a": dropdown_a, 
            "dropdown_b": dropdown_b
        }
