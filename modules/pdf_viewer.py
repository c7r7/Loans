import gradio as gr
import os
import logging
import fitz  # PyMuPDF
from PIL import Image
from openai import OpenAI

# -------------------------------------------------
# Logging config
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---------------------------
# Helpers
# ---------------------------

def get_page_count(pdf_path):
    logging.info(f"Getting page count for PDF: {pdf_path}")
    try:
        doc = fitz.open(pdf_path)
        return doc.page_count
    except Exception as e:
        logging.error(f"Failed to get page count for {pdf_path}: {e}")
        return 1


def render_pdf_page_as_image(pdf_path, page_num):
    """
    Render a single PDF page as an image using PyMuPDF (NO poppler)
    """
    logging.info(f"Rendering PDF page | Path: {pdf_path} | Page: {page_num}")

    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num - 1)

        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    except Exception as e:
        logging.exception(
            f"Failed to render page {page_num} for PDF {pdf_path}"
        )
        return None


def analyze_specific_page(pdf_path, page_num):
    logging.info(f"Analyzing page {page_num} | PDF path: {pdf_path}")

    if not pdf_path or not os.path.exists(pdf_path):
        logging.error(f"PDF path invalid or missing: {pdf_path}")
        return "No PDF loaded", None

    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num - 1)
        page_text = page.get_text()

        if not page_text.strip():
            logging.warning(f"No readable text on page {page_num}")
            return "No readable text on this page.", None

        prompt = f"""
You are a friendly, intelligent financial assistant.
The user is reading page {page_num} of a loan agreement.

PAGE TEXT:
<<<
{page_text[:4000]}
>>>

Task:
1. Identify ONE key commercial risk or insight.
2. Explain it in 2–3 concise sentences.
3. Keep tone clear, professional, and helpful.
"""

        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )

        insight_text = response.choices[0].message.content

        speech = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=insight_text,
        )

        os.makedirs("assets", exist_ok=True)
        audio_path = f"assets/page_{page_num}.mp3"
        speech.stream_to_file(audio_path)

        logging.info(f"Generated audio for page {page_num}: {audio_path}")

        return insight_text, audio_path

    except Exception as e:
        logging.exception(
            f"Analysis failed | PDF: {pdf_path} | Page: {page_num}"
        )
        return f"Error: {e}", None


# ---------------------------
# UI
# ---------------------------

def create_tab():
    with gr.Row():
        # -------- LEFT: PDF IMAGE VIEWER --------
        with gr.Column(scale=2):
            gr.Markdown("### 📄 Document Viewer")

            pdf_image = gr.Image(
                label="PDF Page",
                height=800,
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

        # -------- RIGHT: AI ASSISTANT --------
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 AI Loan Assistant")

            gr.Image(
                value="assets/avatar.png",
                show_label=False,
                width=280,
            )

            advisor_text = gr.Markdown(
                "**Assistant:** Upload a loan document to begin."
            )

            audio_player = gr.Audio(
                label="Voice",
                autoplay=True,
            )

    # ---------------------------
    # Events
    # ---------------------------

    def on_page_change(pdf_path, page_num):
        logging.info(
            f"Page slider changed | Path: {pdf_path} | Page: {page_num}"
        )
        if not pdf_path:
            return None
        return render_pdf_page_as_image(pdf_path, page_num)

    page_slider.change(
        fn=on_page_change,
        inputs=[current_pdf_path, page_slider],
        outputs=pdf_image,
    )

    analyze_btn.click(
        fn=analyze_specific_page,
        inputs=[current_pdf_path, page_slider],
        outputs=[advisor_text, audio_player],
    )

    # ---------------------------
    # Called from app.py
    # ---------------------------

    def update_pdf_state(path):
        logging.info(f"Updating PDF state | Incoming path: {path}")

        if not path or not os.path.exists(path):
            logging.error(f"PDF not found during update: {path}")
            return None, None, gr.Slider(value=1, minimum=1, maximum=1)

        page_count = get_page_count(path)
        first_page_img = render_pdf_page_as_image(path, 1)

        logging.info(
            f"PDF loaded successfully | Pages: {page_count} | Path: {path}"
        )

        return (
            first_page_img,
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
        "pdf_viewer": pdf_image,
        "current_pdf_path": current_pdf_path,
        "page_slider": page_slider,
        "update_fn": update_pdf_state,
    }
