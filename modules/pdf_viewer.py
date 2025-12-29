import gradio as gr
import os
import logging
import base64
from pypdf import PdfReader
from openai import OpenAI

# Global reference to API KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ---------------------------
# Helpers
# ---------------------------

def get_page_count(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception:
        return 1


def analyze_specific_page(pdf_path, page_num):
    if not pdf_path or not os.path.exists(pdf_path):
        return "No PDF", None

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)

        idx = int(page_num) - 1
        if idx < 0 or idx >= total_pages:
            return "Invalid Page Number", None

        page_text = reader.pages[idx].extract_text()
        if not page_text:
            return "No text found on this page (scanned image?)", None

        prompt = f"""
You are a cute, intelligent anime financial assistant.
The user is looking at Page {page_num} of a loan agreement.
Here is the text of the page:
<<<
{page_text[:4000]}
>>>

Your task:
1. Identify the single most important "Insight" or "Risk" on this page.
2. Explain it in a helpful, conversational, anime-style voice.
3. Keep it short (2-3 sentences max).
"""

        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        insight_text = response.choices[0].message.content

        speech = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=insight_text,
        )

        os.makedirs("assets", exist_ok=True)
        audio_path = f"assets/speech_page_{page_num}.mp3"
        speech.stream_to_file(audio_path)

        return insight_text, audio_path

    except Exception as e:
        logging.exception("Page analysis failed")
        return f"Error analyzing page: {e}", None


# ---------------------------
# UI
# ---------------------------

def create_tab():
    with gr.Row():
        # ---------- LEFT: PDF VIEWER ----------
        with gr.Column(scale=2):
            gr.Markdown("### 📄 Document Viewer")

            pdf_display = gr.HTML(
                value="<div style='color:gray'>No PDF loaded</div>",
                label="PDF View",
            )

            current_pdf_path = gr.State(value=None)

            with gr.Row():
                page_slider = gr.Slider(
                    minimum=1,
                    maximum=1,
                    step=1,
                    value=1,
                    label="Go to Page",
                )
                analyze_btn = gr.Button("✨ Analyze Page", variant="primary")

        # ---------- RIGHT: ASSISTANT ----------
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 AI Loan Assistant")

            gr.Image(
                value="assets/avatar.png",
                show_label=False,
                width=300,
            )

            advisor_text = gr.Markdown(
                "**Assistant:** *Upload a document and I’ll help analyze it page by page!*"
            )

            audio_player = gr.Audio(
                label="Voice",
                autoplay=True,
                visible=True,
            )

    # ---------------------------
    # Events
    # ---------------------------

    analyze_btn.click(
        fn=analyze_specific_page,
        inputs=[current_pdf_path, page_slider],
        outputs=[advisor_text, audio_player],
    )

    # ---------------------------
    # Update function (called from app.py)
    # ---------------------------

    def update_pdf_state(path):
        logging.info("Rendering inline PDF via base64: %s", path)

        if not path or not os.path.exists(path):
            return (
                "<div style='color:red'>PDF not found</div>",
                None,
                gr.Slider(value=1, minimum=1, maximum=1),
            )

        page_count = get_page_count(path)

        with open(path, "rb") as f:
            b64_pdf = base64.b64encode(f.read()).decode("utf-8")

        iframe_html = f"""
        <iframe
            src="data:application/pdf;base64,{b64_pdf}"
            type="application/pdf"
            width="100%"
            height="800"
            style="border:none;"
            loading="lazy">
        </iframe>
        """


        return (
            iframe_html,
            path,
            gr.Slider(
                minimum=1,
                maximum=page_count,
                value=1,
                step=1,
                label="Go to Page",
            ),
        )

    return {
        "pdf_viewer": pdf_display,
        "current_pdf_path": current_pdf_path,
        "page_slider": page_slider,
        "update_fn": update_pdf_state,
    }
