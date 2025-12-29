import gradio as gr
from modules import loans, tables, comparison, pdf_viewer, data
import os

def main():
    # Use the default plain Gradio theme with orange accents
    theme = gr.themes.Default(primary_hue="orange")
    
    with gr.Blocks(title="Loan Dashboard", theme=theme) as demo:
        gr.Markdown("# 🏦 Loan Management Dashboard")
        
        # Tabs Container
        tabs_container = gr.Tabs()
        
        with tabs_container:
            # -- Tab 1: Loans --
            with gr.Tab("Loans", id="tab_loans"):
                loans_components = loans.create_tab()
                
            # -- Tab 2: Tables --
            with gr.Tab("Tables", id="tab_tables"):
                tables_components = tables.create_tab()
                
            # -- Tab 3: Comparison --
            with gr.Tab("Comparision", id="tab_comp"):
                comparison_components = comparison.create_tab()

            # -- Tab 4: PDF Viewer --
            with gr.Tab("PDF Viewer", id="tab_pdf"):
                pdf_viewer_components = pdf_viewer.create_tab()

        # --- ORCHESTRATION ---
        
        # 1. SAVE & REGISTER
        def handle_save_and_register(file_obj, json_data):
            if file_obj is None:
                return gr.HTML("No file"), None, gr.Slider(), gr.Dataframe()
            
            # Save File
            saved_path = loans.save_pdf_handler(file_obj)
            
            # Register in Database
            filename = os.path.basename(file_obj.name)
            if json_data:
                data.add_loan(filename, saved_path, json_data)
            
            # Update PDF Viewer State 
            iframe, path, slider = pdf_viewer_components["update_fn"](saved_path)
            
            # Refresh Table (keep current query empty)
            new_table_data = data.get_dataframe_data("")
            
            return iframe, path, slider, new_table_data

        loans_components["save_btn"].click(
            fn=handle_save_and_register,
            inputs=[loans_components["pdf_uploader"], loans_components["json_output"]],
            outputs=[
                pdf_viewer_components["pdf_viewer"],
                pdf_viewer_components["current_pdf_path"],
                pdf_viewer_components["page_slider"],
                tables_components["loan_table"]
            ]
        )
        
        # 2. TABLE SELECTION LOGIC
        def handle_table_select(evt: gr.SelectData, current_query):
            # Column Mapping (Must match tables.py headers):
            # 0:Filename, 1:Borrower, 2:Lender, 3:Amount, 4:Interest, 5:Maturity, 6:Action_PDF, 7:Action_JSON
            
            if evt is None: return gr.HTML(), None, gr.Slider(), None, gr.Tabs()
            
            row_idx, col_idx = evt.index
            
            # Since table might be filtered, we need to find the REAL entry based on Filename (Col 0)
            # But Gradio select gives us the index relative to the *visible* dataframe.
            # We need the value of the first cell in that row.
            # However, `evt.value` is the cell value clicked. We can't easily get the neighbor cell value from `SelectData` alone in standard Gradio without generic state.
            
            # Workaround: Retrieve the visible dataframe first? Expensive.
            # Alternative: We assume the user clicks "View PDF" or "View JSON".
            # If we used the `tables_components["loan_table"]` as input, we could get the full data.
            pass 
        
        # Improved Selection Logic: passing the actual dataframe value to find the row
        def handle_table_select_real(evt: gr.SelectData, df_value):
            if evt is None: return [gr.skip()] * 5
            
            row_idx, col_idx = evt.index
            try:
                # Get Filename from Column 0 of the selected row
                filename = df_value.iloc[row_idx, 0] 
                entry = data.get_entry_by_filename(filename)
                
                if not entry: return [gr.skip()] * 5
                
                # Column 6: View PDF
                if col_idx == 6:
                    saved_path = entry["filepath"]
                    iframe, path, slider = pdf_viewer_components["update_fn"](saved_path)
                    return iframe, path, slider, entry["full_json"], gr.Tabs(selected="tab_pdf")

                # Column 7: View JSON
                elif col_idx == 7:
                    return gr.HTML(), None, gr.Slider(), entry["full_json"], gr.Tabs(selected="tab_tables")
                    
            except Exception as e:
                print(f"Selection Error: {e}")
                
            return [gr.skip()] * 5

        tables_components["loan_table"].select(
            fn=handle_table_select_real,
            inputs=[tables_components["loan_table"]],
            outputs=[
                pdf_viewer_components["pdf_viewer"],
                pdf_viewer_components["current_pdf_path"],
                pdf_viewer_components["page_slider"],
                tables_components["json_view"],
                tabs_container
            ]
        )

    return demo

if __name__ == "__main__":
    app = main()
    app.launch(allowed_paths=["."])
