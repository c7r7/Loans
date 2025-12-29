import gradio as gr
from modules import loans, tables, comparison, pdf_viewer, data
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def main():
    theme = gr.themes.Default(primary_hue="orange")

    # ⛔ Do NOT pass theme here (Gradio 6.x warning)
    with gr.Blocks(title="Loan Dashboard") as demo:
        gr.Markdown("# 🏦 Loan Management Dashboard")

        tabs_container = gr.Tabs()

        with tabs_container:
            # ---- Loans Tab ----
            with gr.Tab("Loans", id="tab_loans"):
                loans_components = loans.create_tab()

            # ---- Tables Tab ----
            with gr.Tab("Tables", id="tab_tables"):
                tables_components = tables.create_tab()

            # ---- Comparison Tab ----
            with gr.Tab("Comparison", id="tab_comp"):
                comparison_components = comparison.create_tab()

            # ---- PDF Viewer Tab ----
            with gr.Tab("PDF Viewer", id="tab_pdf"):
                pdf_viewer_components = pdf_viewer.create_tab()

        # SAVE & REGISTER FLOW
        # ======================================================
        def handle_save_and_register(file_obj, json_data):
            if file_obj is None:
                return (
                    "<div>No file</div>",
                    None,
                    gr.Slider(value=1, minimum=1, maximum=2),
                    tables.get_truncated_data(""),
                )

            # Save PDF
            saved_path = loans.save_pdf_handler(file_obj)

            # Register metadata
            filename = os.path.basename(file_obj.name)
            if json_data:
                data.add_loan(filename, saved_path, json_data)

            # 🔑 Inline PDF render (base64)
            iframe, path, slider = pdf_viewer_components["update_fn"](saved_path)

            new_table_data = tables.get_truncated_data("")

            return (
                iframe,          # PDF viewer HTML
                path,            # current_pdf_path
                slider,          # page slider
                new_table_data,  # table refresh
            )

        # Chain: Extract -> Success -> Save
        # 1. User clicks Process Button -> Calls Extract
        extract_event = loans_components["process_btn"].click(
            fn=loans.extract_metadata_handler,
            inputs=[loans_components["pdf_uploader"]],
            outputs=[loans_components["status_output"], loans_components["json_output"]]
        )
        
        # 2. On Success of Extract -> Calls Save & Register
        extract_event.success(
            fn=handle_save_and_register,
            inputs=[
                loans_components["pdf_uploader"],
                loans_components["json_output"],
            ],
            outputs=[
                pdf_viewer_components["pdf_viewer"],
                pdf_viewer_components["current_pdf_path"],
                pdf_viewer_components["page_slider"],
                tables_components["loan_table"],
            ],
        )


        # ======================================================
        # TABLE → PDF / JSON NAVIGATION
        # ======================================================
        def handle_table_select_real(evt: gr.SelectData, df_value):
            if evt is None:
                return [gr.skip()] * 5

            row_idx, col_idx = evt.index

            try:
                filename = df_value.iloc[row_idx, 0]
                entry = data.get_entry_by_filename(filename)

                if not entry:
                    return [gr.skip()] * 5

                # View PDF
                if col_idx == 6:
                    saved_path = entry["filepath"]
                    iframe, path, slider = pdf_viewer_components["update_fn"](saved_path)

                    return (
                        iframe,
                        path,
                        slider,
                        entry["full_json"],
                        gr.Tabs(selected="tab_pdf"),
                    )

                # View JSON
                if col_idx == 7:
                    return (
                        gr.skip(),
                        gr.skip(),
                        gr.skip(),
                        entry["full_json"],
                        gr.Tabs(selected="tab_tables"),
                    )

            except Exception as e:
                logging.exception("Table selection error")

            return [gr.skip()] * 5

        tables_components["loan_table"].select(
            fn=handle_table_select_real,
            inputs=[tables_components["loan_table"]],
            outputs=[
                pdf_viewer_components["pdf_viewer"],
                pdf_viewer_components["current_pdf_path"],
                pdf_viewer_components["page_slider"],
                tables_components["json_view"],
                tabs_container,
            ],
        )

    return demo


if __name__ == "__main__":
    app = main()
    app.launch()