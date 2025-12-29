import gradio as gr
from modules import data

# Helper to truncate text
def truncate_text(text, limit=30):
    s = str(text)
    return s[:limit] + "..." if len(s) > limit else s

def get_truncated_data(query=None):
    raw_data = data.get_dataframe_data(query)
    processed_rows = []
    for row in raw_data:
        # row structure: [Filename, Borrower, Lender, Amount, Interest, Maturity, Action1, Action2]
        # Preserve Filename (index 0) for lookup, truncate others
        new_row = []
        for i, item in enumerate(row):
            if i == 0:
                new_row.append(item)
            else:
                new_row.append(truncate_text(item))
        processed_rows.append(new_row)
    return processed_rows

def create_tab():
    with gr.Column():
        gr.Markdown("### 📊 Loan Portfolio")
        
        # Search Bar
        with gr.Row():
            search_box = gr.Textbox(
                label="Search Loans", 
                placeholder="Type to filter by Borrower, Amount, etc...",
                show_label=True
            )
            refresh_btn = gr.Button("🔄 Refresh Table")

        # The main data table
        # Updated Columns: Filename, Borrower, Lender, Amount, Interest, Maturity
        loan_table = gr.Dataframe(
            headers=["Filename", "Borrower", "Lender", "Amount", "Interest", "Maturity", "Action: PDF", "Action: JSON"],
            datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
            value=get_truncated_data(),
            interactive=False,
            row_count=10
        )
        
        # Area to show JSON insights if selected
        gr.Markdown("### 🔍 Selected Loan Insights")
        json_view = gr.JSON(label="Loan Data")

        # --- Logic ---
        
        def refresh_data(query):
            return get_truncated_data(query)
        
        # Refresh on button click or search change
        refresh_btn.click(fn=refresh_data, inputs=[search_box], outputs=[loan_table])
        search_box.change(fn=refresh_data, inputs=[search_box], outputs=[loan_table])
        
        return {
            "loan_table": loan_table,
            "json_view": json_view,
            "refresh_btn": refresh_btn,
            "search_box": search_box
        }
