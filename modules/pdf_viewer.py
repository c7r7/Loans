import gradio as gr
import os
from pypdf import PdfReader
from openai import OpenAI

# Global reference to API KEY (should be passed better, but keeping style)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def render_pdf(pdf_path):
    """
    Returns an HTML iframe to display the PDF.
    """
    if pdf_path is None:
        return "<div>No PDF loaded</div>"
    
    # For Gradio file server, we use absolute paths
    abs_path = os.path.abspath(pdf_path)
    # Windows paths need to be converted to forward slashes for the URL
    rel_path = abs_path.replace("\\", "/")
    
    iframe = f'<iframe src="/file={rel_path}" width="100%" height="800px"></iframe>'
    return iframe

def get_page_count(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except:
        return 1

def analyze_specific_page(pdf_path, page_num):
    """
    Extracts text from a specific page, runs AI summary + TTS.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return "No PDF", None
    
    try:
        # Extract Text from Page
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        
        # Adjust 1-based index to 0-based
        idx = int(page_num) - 1
        if idx < 0 or idx >= total_pages:
            return "Invalid Page Number", None
            
        page_text = reader.pages[idx].extract_text()
        if not page_text:
            return "No text found on this page (scanned image?)", None
            
        # Call LLM
        prompt = f"""
You are a cute, intelligent anime financial assistant.
The user is looking at Page {page_num} of a loan agreement.
Here is the text of the page:
<<<
{page_text[:4000]}
>>>

Your task:
1. Identify the single most important "Insight" or "Risk" on this page.
2. Explain it in a helpful, conversational, anime-style voice (alert but friendly).
3. Keep it short (2-3 sentences max).
"""
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Chat Completion
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        insight_text = response.choices[0].message.content
        
        # Text-to-Speech
        speech_response = client.audio.speech.create(
            model="tts-1",
            voice="nova", # 'nova' is energetic/female
            input=insight_text
        )
        
        audio_path = f"assets/speech_page_{page_num}.mp3"
        speech_response.stream_to_file(audio_path)
        
        return insight_text, audio_path
        
    except Exception as e:
        return f"Error analyzing page: {str(e)}", None


def create_tab():
    with gr.Row():
        # -- Left Column: PDF Viewer --
        with gr.Column(scale=2):
            gr.Markdown("### 📄 Document Viewer")
            pdf_display = gr.HTML(label="PDF View", value=render_pdf(None))
            
            # Hidden state to store current PDF path
            current_pdf_path = gr.State(value=None)
            
            # Page Selector (Simulated sync)
            with gr.Row():
                page_slider = gr.Slider(minimum=1, maximum=100, step=1, label="Go to Page", value=1)
                analyze_btn = gr.Button("✨ Analyze Page", variant="primary")

        # -- Right Column: AI Anime Assistant --
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 AI Loan Assistant")
            
            # Avatar Image
            # Ensure assets/avatar.png exists
            avatar_display = gr.Image(value="assets/avatar.png", label="Assistant", show_label=False, width=300)
            
            # Assistant Output
            advisor_text = gr.Markdown("**Assistant:** *Hello! Upload a document and I'll help you analyze it page by page!*")
            audio_player = gr.Audio(label="Voice", autoplay=True, visible=True)

    # --- Interaction Logic ---
    
    # When analyze button clicked
    analyze_btn.click(
        fn=analyze_specific_page,
        inputs=[current_pdf_path, page_slider],
        outputs=[advisor_text, audio_player]
    )
    
    # Helper to update slider max when new PDF loaded
    def update_pdf_state(path):
        count = get_page_count(path)
        # Return: iframe_html, pdf_path_state, slider_update
        return render_pdf(path), path, gr.Slider(maximum=count, value=1)

    return {
        "pdf_viewer": pdf_display,         # To update iframe
        "current_pdf_path": current_pdf_path, # To store path
        "page_slider": page_slider,        # To update limits
        "update_fn": update_pdf_state      # Function to call from app.py
    }
