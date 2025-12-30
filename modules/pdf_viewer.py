import gradio as gr
import os
import json
import logging
import fitz  # PyMuPDF
from PIL import Image
from openai import OpenAI
import re

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEF_START_RE = re.compile(r'^"\w+')
ENUM_RE = re.compile(r'^\([a-zA-Z0-9]+\)')

# -------------------------------------------------
# PDF Utilities
# -------------------------------------------------

def extract_text_structure(page):
    spans = []
    lines = []

    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" not in block:
            continue

        for line in block["lines"]:
            line_span_ids = []
            line_rects = []

            for span in line["spans"]:
                text = span["text"].strip()
                if not text:
                    continue

                span_id = len(spans)
                spans.append({
                    "id": span_id,
                    "text": text,
                    "bbox": fitz.Rect(span["bbox"])
                })

                line_span_ids.append(span_id)
                line_rects.append(fitz.Rect(span["bbox"]))

            if line_span_ids:
                lines.append({
                    "span_ids": line_span_ids,
                    "rects": line_rects,
                    "text": " ".join(spans[i]["text"] for i in line_span_ids)
                })

    logging.info(f"Extracted {len(spans)} spans across {len(lines)} lines")
    return spans, lines


def render_pdf_page_as_image(pdf_path, page_num, page_highlights=None):
    logging.info(
        f"Rendering page {page_num} | Highlights: {bool(page_highlights)}"
    )

    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num - 1)

    # ❗ Never reuse annotations across renders
    for annot in page.annots() or []:
        if annot.type[0] == fitz.PDF_ANNOT_HIGHLIGHT:
            page.delete_annot(annot)

    if page_highlights:
        spans, lines = extract_text_structure(page)
        used_lines = set()
        MAX_LINES = 6

        for span_id in page_highlights:
            for i, line in enumerate(lines):
                if span_id in line["span_ids"] and i not in used_lines:
                    rects = []
                    lines_used = 0

                    for j in range(i, len(lines)):
                        text = lines[j]["text"].strip()

                        if j > i and text.startswith('"'):
                            break
                        if j > i and ENUM_RE.match(text):
                            break
                        if lines_used >= MAX_LINES:
                            break

                        rects.extend(lines[j]["rects"])
                        lines_used += 1

                        if "." in text:
                            break

                    for r in rects:
                        page.add_highlight_annot(r)

                    used_lines.add(i)
                    break

    pix = page.get_pixmap(dpi=150)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def get_page_count(pdf_path):
    return fitz.open(pdf_path).page_count

# -------------------------------------------------
# AI Analysis (PROMPT UNCHANGED)
# -------------------------------------------------

def analyze_specific_page(pdf_path, page_num):
    logging.info(f"Analyzing page {page_num}")

    doc = fitz.open(pdf_path)
    page = doc.load_page(page_num - 1)

    spans, _ = extract_text_structure(page)

    if not spans:
        return "No readable text.", None, [], [], []

    span_dump = "\n".join(
        f"[{s['id']}] {s['text']}" for s in spans
    )

    prompt = f"""
You are an expert loan documentation analyst.

You are analyzing EXACTLY ONE PAGE of a loan agreement.

Below is the page broken into ORDERED TEXT SPANS.
Each span has a UNIQUE numeric ID.
Span IDs are ONLY for internal alignment and MUST NEVER appear in the summary text.

========================
PAGE TEXT SPANS
========================
{span_dump}

========================
YOUR TASK
========================

Return a VALID JSON object ONLY.

Required format:
{{
  "summary_paragraph": string,
  "highlight_span_ids": array of integers,
  "risk_types": array of strings,
  "clauses": array of strings
}}

========================
RULES — READ CAREFULLY
========================

1. SUMMARY PARAGRAPH
- Write ONE coherent paragraph (5–7 sentences).
- The FIRST sentence is a high-level introduction to the page.
- EACH remaining sentence MUST correspond to EXACTLY ONE highlighted span.
- The summary MUST read naturally, like a professional voice-over.
- ❗ DO NOT mention span numbers, IDs, brackets, or references of any kind.
- ❗ Do NOT say things like “Span 12”, “[3]”, or “this section”.
- The listener should NOT know span IDs exist.

2. HIGHLIGHT SPANS
- Short page → select 1–3 spans
- Dense page → select 4–6 spans
- highlight_span_ids MUST contain ONLY integer IDs from the span list above.
- The ORDER of span IDs MUST match the order of the corresponding sentences in the summary.

3. RISK TYPES
Choose all that apply from:
- Legal
- Financial
- Operational
- Regulatory

4. CLAUSES
- Extract clause names or defined terms EXACTLY as written.
- Example: "Material Adverse Effect", "Interest Rate"
- If none are present, return an empty array.

========================
STRICT OUTPUT RULES
========================
- Output MUST be valid JSON.
- NO markdown.
- NO explanations.
- NO extra keys.
- NO span IDs or references inside the summary text.

If any rule is violated, the output is invalid.
"""


    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    data = json.loads(response.choices[0].message.content)

    speech = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=data["summary_paragraph"],
    )

    os.makedirs("assets", exist_ok=True)
    audio_path = f"assets/page_{page_num}.mp3"
    speech.stream_to_file(audio_path)

    return (
        data["summary_paragraph"],
        audio_path,
        data["highlight_span_ids"],
        data.get("risk_types", []),
        data.get("clauses", []),
    )

# -------------------------------------------------
# UI
# -------------------------------------------------

def create_tab():
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### 📄 Document Viewer")
            pdf_image = gr.Image(height=800)

            current_pdf_path = gr.State(None)
            highlights_by_page = gr.State({})

            with gr.Row():
                page_slider = gr.Slider(1, 1, step=1, label="Go to Page")
                analyze_btn = gr.Button("✨ Analyze Page", variant="primary")

        with gr.Column(scale=1):
            gr.Markdown("### 🤖 AI Loan Assistant")
            risk_md = gr.Markdown("")
            clause_md = gr.Markdown("")
            summary_md = gr.Markdown("")
            audio_player = gr.Audio(autoplay=True)

    def on_page_change(pdf_path, page, highlight_map):
        page_highlights = highlight_map.get(page, [])
        return render_pdf_page_as_image(pdf_path, page, page_highlights)

    page_slider.change(
        fn=on_page_change,
        inputs=[current_pdf_path, page_slider, highlights_by_page],
        outputs=pdf_image,
    )

    def on_analyze(pdf_path, page, highlight_map):
        summary, audio, span_ids, risks, clauses = analyze_specific_page(
            pdf_path, page
        )

        highlight_map = dict(highlight_map)
        highlight_map[page] = span_ids

        img = render_pdf_page_as_image(pdf_path, page, span_ids)

        return (
            img,
            highlight_map,
            f"⚠️ **Risk Types:** {' | '.join(risks)}",
            f"📌 **Clauses:** {', '.join(clauses)}",
            summary,
            audio,
        )

    analyze_btn.click(
        fn=on_analyze,
        inputs=[current_pdf_path, page_slider, highlights_by_page],
        outputs=[
            pdf_image,
            highlights_by_page,
            risk_md,
            clause_md,
            summary_md,
            audio_player,
        ],
    )

    def update_pdf_state(path):
        page_count = get_page_count(path)
        img = render_pdf_page_as_image(path, 1)
        return img, path, gr.Slider(1, page_count, value=1, step=1)

    return {
        "pdf_viewer": pdf_image,
        "current_pdf_path": current_pdf_path,
        "page_slider": page_slider,
        "update_fn": update_pdf_state,
    }
