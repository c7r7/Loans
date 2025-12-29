import gradio as gr
import os
import json
import re
from pypdf import PdfReader
from openai import OpenAI
import shutil

# --- Configuration ---
# (Ideally this should be an env var, but keeping it here as per previous user edits)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Remove-Item -Recurse -Force modules\__pycache__
# Remove-Item -Recurse -Force __pycache__

# --- Logic Functions ---

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using pypdf.
    """
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def analyze_loan_agreement(text_chunk):
    """
    Reads a loan agreement like a human analyst and extracts all
    material, decision-relevant information into dynamic JSON.
    """
    # LLM Prompt (Schema-Free)
    prompt = """
You are an expert legal and financial analyst specializing in commercial loan agreements.

Your task is to READ the provided loan agreement line by line and extract ALL material, decision-relevant information into a SINGLE structured JSON object.

This task uses a HYBRID approach:
1. A CORE loan agreement schema to ensure standard terms are always captured
2. A DYNAMIC extraction layer to ensure NO important, deal-specific, or non-standard information is missed simply because it does not fit the schema

The goal is that a human reader can understand the full commercial and legal substance of the loan WITHOUT reading the original document.

--------------------------------
CRITICAL RULES
--------------------------------
- Output VALID JSON ONLY
- Do NOT invent or infer information
- Dates → YYYY-MM-DD
- Numbers → numeric only
- Boolean → true / false

--------------------------------
PART 1: CORE LOAN SCHEMA (ALWAYS INCLUDE)
--------------------------------
{
  "core_loan_terms": {
    "borrower": null,
    "administrative_agent": null,
    "lenders": null,
    "facility_type": null,
    "loan_amount": null,
    "currency": null,
    "interest_type": null,
    "benchmark_rate": null,
    "margin": {
      "min": null,
      "max": null
    },
    "fees": null,
    "maturity_or_termination_date": null,
    "repayment_and_prepayment": null,
    "security_or_collateral": null,
    "guarantees": null,
    "financial_covenants": null,
    "non_financial_covenants": null,
    "events_of_default": null,
    "conditions_precedent": null,
    "governing_law": null,
    "jurisdiction": null,
    "assignment_and_transferability": null
  }
}

--------------------------------
PART 2: DYNAMIC DEAL-SPECIFIC EXTRACTION
--------------------------------
Extract ANY additional material, bespoke, or deal-specific information.

--------------------------------
PART 3: HUMAN-READABLE HIGHLIGHTS
--------------------------------
Summarize key economics, risks, and unusual features.

--------------------------------
INPUT DOCUMENT
--------------------------------
<<<
{DOCUMENT_TEXT}
>>>

--------------------------------
OUTPUT
--------------------------------
Return ONE SINGLE JSON object.
"""
    prompt = prompt.replace("{DOCUMENT_TEXT}", text_chunk[:12000])

    # LLM Path (Primary)
    if OPENAI_API_KEY:
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0
            )
            extracted_json = response.choices[0].message.content
            return json.loads(extracted_json), "✅ Analysis complete (LLM – schema-free)."
        except Exception as e:
            return {}, f"❌ LLM Error: {e}"

    # Regex Fallback (Heuristic)
    fallback_data = {}
    borrower_match = re.search(r"(Borrower|Borrowers)\s*[:\-]?\s*(.+)", text_chunk, re.IGNORECASE)
    if borrower_match:
        fallback_data["borrower"] = borrower_match.group(2).strip()

    amount_match = re.search(r"(USD|EUR|GBP|\$)\s?([0-9,]{4,})", text_chunk)
    if amount_match:
        fallback_data["loan_amount"] = amount_match.group(2).replace(",", "")
        fallback_data["currency"] = "USD" if "$" in amount_match.group(1) else amount_match.group(1)

    law_match = re.search(r"governed by the laws? of ([A-Za-z\s]+)", text_chunk, re.IGNORECASE)
    if law_match:
        fallback_data["governing_law"] = law_match.group(1).strip()

    return fallback_data, "⚠️ Limited analysis (regex fallback, schema-free)."

def extract_metadata_handler(file_obj):
    """
    Extracts text from PDF and runs schema-free loan analysis.
    """
    if file_obj is None:
        return "No file uploaded.", None

    pdf_text = extract_text_from_pdf(file_obj.name)
    if "Error reading PDF" in pdf_text:
        return f"❌ {pdf_text}", None

    extracted_data, status_note = analyze_loan_agreement(pdf_text)
    status_msg = f"{status_note} Processed {len(pdf_text)} characters."
    return status_msg, extracted_data

def save_pdf_handler(file_obj):
    """
    Saves the uploaded file to a 'saved_pdfs' directory.
    Returns the path to the saved file.
    """
    if file_obj is None:
        return None
    
    # Create directory if not exists
    save_dir = "saved_pdfs"
    os.makedirs(save_dir, exist_ok=True)
    
    # Get original filename
    filename = os.path.basename(file_obj.name)
    destination = os.path.join(save_dir, filename)
    
    # Copy file
    try:
        shutil.copy(file_obj.name, destination)
        return destination
    except Exception as e:
        print(f"Error saving file: {e}")
        return None

def on_file_upload_change(file_obj):
    """
    Event handler for file upload change.
    Enables Buttons if a file is present.
    """
    if file_obj is not None:
        return gr.Button(interactive=True), gr.Button(interactive=True), "File uploaded. Ready to extract/save.", None
    else:
        return gr.Button(interactive=False), gr.Button(interactive=False), "Please upload a PDF file.", None

# --- UI Builder ---

def create_tab():
    with gr.Column():
        gr.Markdown("### 📄 PDF Upload & Metadata Extraction")
        
        pdf_uploader = gr.File(
            label="Upload Loan PDF",
            file_types=[".pdf"],
            file_count="single",
            type="filepath"
        )
        
        with gr.Row():
            extract_btn = gr.Button("Extract Metadata", variant="primary", interactive=False)
            save_btn = gr.Button("Save PDF", variant="secondary", interactive=False)
        
        status_output = gr.Textbox(
            label="Status",
            placeholder="Upload status will appear here...",
            lines=1,
            interactive=False
        )
        
        json_output = gr.JSON(
            label="Extracted Metadata (JSON)",
            value=None
        )
        
        # Events
        pdf_uploader.change(
            fn=on_file_upload_change,
            inputs=[pdf_uploader],
            outputs=[extract_btn, save_btn, status_output, json_output]
        )
        
        extract_btn.click(
            fn=extract_metadata_handler,
            inputs=[pdf_uploader],
            outputs=[status_output, json_output]
        )
        
        # We return the buttons and inputs so app.py can wire them to other tabs
        return {
            "ui": None, 
            "pdf_uploader": pdf_uploader,
            "save_btn": save_btn,
            "json_output": json_output
        }
