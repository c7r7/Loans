# LoanIQ: Intelligent Loan Management Dashboard 🏦

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Gradio](https://img.shields.io/badge/Frontend-Gradio-orange)
![OpenAI](https://img.shields.io/badge/AI-OpenAI%20GPT--4-green)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**LoanIQ** is a next-generation loan document analysis platform built for the **LMA EDGE Hackathon**. It leverages advanced AI to transform static PDF loan agreements into structured, actionable data, providing bankers and analysts with an "always-on" junior analyst that can read, extract, and speak summaries of complex legal documents.

---

## 🚀 Key Features

### 1. 📄 Smart PDF Ingestion (`Loans` Tab)
- **Drag-and-Drop Interface:** Easily upload complex loan agreements (PDF).
- **Hybrid Extraction Engine:** Combines **OpenAI's GPT-4** for deeper semantic understanding with **Regex heuristics** for 100% reliable extraction of critical terms (Borrowers, Amounts, Dates).
- **Automated Structuring:** Instantly converts unstructured text into a standardized JSON schema.

### 2. 🤖 AI Analyst & PDF Viewer (`PDF Viewer` Tab)
- **Interactive Analysis:** Select any page to receive an instant AI briefing.
- **Risk Detection:** Automatically flags **Legal, Financial, and Operational risks**.
- **Clause Extraction:** Identifies and lists key clauses (e.g., "Material Adverse Effect", "Negative Pledge").
- **Voice Summaries:** Uses **OpenAI Audio generation (TTS)** to create professional voice-overs of page summaries, allowing for multitasking.
- **Visual Highlights:** Highlights relevant sections on the page image dynamically.

### 3. 📊 Data Management (`Tables` Tab)
- **Centralized Database:** Stores all extracted metadata in a local JSON database (`loan_database.json`).
- **Tabular View:** View, sort, and manage processed loans in a clean spreadsheet-like interface.

### 4. ⚖️ Interactive Comparison (`Comparison` Tab)
- **Side-by-Side View:** Select multiple loans to compare their terms directly.
- **Visual Diff:** Immediately spot differences in interest rates, margins, and covenants.
- **Export Ready:** Generate comparison reports for investment committees.

---

## 🛠️ Technology Stack

- **Frontend/UI:** [Gradio](https://gradio.app/) - For a responsive, accessible, and beautiful web interface (Custom "Orange" Theme).
- **Backend Logic:** Python.
- **AI & ML:**
  - **OpenAI API:** GPT-4 Turbo / GPT-5 (Preview) for text analysis.
  - **OpenAI TTS:** For high-fidelity audio generation.
  - **PyMuPDF (Fitz):** For robust PDF text and layout extraction.
- **Containerization:** Docker.

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9 or higher.
- An **OpenAI API Key** with access to GPT-4 models.

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/LoanIQ.git
cd LoanIQ
```

### 2. Setting up the Environment
It is recommended to use a virtual environment.
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Navigate to the source directory and install requirements.
```bash
cd Loans
pip install -r requirements.txt
```

### 4. Configure API Key
Set your OpenAI API key as an environment variable.
**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-proj-..."
```
**Mac/Linux:**
```bash
export OPENAI_API_KEY="sk-proj-..."
```
*Alternatively, you can create a `.env` file in the `Loans/` directory (though the code primarily checks system env vars first).*

### 5. Run the Application
```bash
python app.py
```
The application will launch locally at `http://localhost:8080`.

---

## 📂 Project Structure

```
LoanIQ/
├── Dockerfile              # Container configuration
├── .dockerignore
├── Loans/
│   ├── app.py              # Main application entry point (Gradio)
│   ├── loan_database.json  # Local database for extracted loan data
│   ├── requirements.txt    # Python dependencies
│   ├── modules/            # Business logic modules
│   │   ├── loans.py        # PDF extraction & data handling
│   │   ├── pdf_viewer.py   # Page rendering & AI analysis
│   │   ├── tables.py
|   |   ├── comparision.py # Data display logic
│   ├── assets/             # Generated audio files (mp3)
│   └── saved_pdfs/         # Storage for uploaded documents
└── README.md               # Project documentation
```

---

## 🔮 Roadmap / Future Features
- **RAG Implementation:** Chat with your documents using Retrieval-Augmented Generation.
- **Cloud Deployment:** seamless deployment to Google Cloud Run or AWS.

---

## 📝 License
This project is created for the **LMA EDGE Hackathon**.

---
*Built with ❤️ by Attention Seekers*
