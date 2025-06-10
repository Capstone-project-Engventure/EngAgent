import os
import uuid
import json
from pathlib import Path
from datetime import datetime

import pdfplumber
import docx2txt
from pptx import Presentation
import pandas as pd

from langchain.embeddings import VertexAIEmbeddings, HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.schema import Document

# -------------------------
# Configuration
# -------------------------
DATA_DIR = Path("data")
CRAWL_DATE = datetime.utcnow().isoformat()

# Source directories and files
SOURCES = {
    "grammar_vocab": {
        "path": DATA_DIR / "google_drive" / "bank_exercises",
        "exts": [".pdf", ".docx"],
        "type": "grammar_vocab",
    },
    "vocab_csv": {
        "path": DATA_DIR / "vocabs" / "vocab.csv",
        "type": "vocabulary",
    },
    "reading_slides": {
        "path": DATA_DIR / "Reading_Comprehension_Slides",
        "exts": [".pptx"],
        "type": "reading",
    },
    "listening_transcripts": {
        "path": DATA_DIR / "Listening_Transcripts",
        "exts": [".txt"],
        "type": "listening",
    },
    "writing_exams": {
        "path": DATA_DIR / "google_drive" / "exam_bank",
        "exts": [".pdf", ".docx"],
        "type": "writing",
    },
    "speaking_scripts": {
        "path": DATA_DIR / "google_drive" / "Speaking_Scripts.md",
        "type": "speaking",
    },
}


# -------------------------
# Extraction functions
# -------------------------
def extract_pdf(path: Path) -> str:
    """Extract plain text from a PDF file."""
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def extract_docx(path: Path) -> str:
    """Extract plain text from a DOCX file."""
    return docx2txt.process(str(path))


def extract_pptx(path: Path) -> str:
    """Extract concatenated text from PPTX slides."""
    text = ""
    prs = Presentation(str(path))
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text


# -------------------------
# Preprocessing & Chunking
# -------------------------
def clean_text(txt: str) -> str:
    """Remove headers, footers, ads and normalize unicode."""
    lines = [l.strip() for l in txt.splitlines()]
    lines = [l for l in lines if len(l.split()) > 2]
    text = "\n".join(lines)
    return text.replace("ADVERTISEMENT", "")


def chunk_text(txt: str, min_words=100, max_words=300, overlap=0.2) -> list[str]:
    """Split text into overlapping chunks preserving context."""
    words = txt.split()
    size = max_words
    step = int(size * (1 - overlap))
    chunks = []
    for i in range(0, len(words), step):
        piece = words[i : i + size]
        if len(piece) >= min_words:
            chunks.append(" ".join(piece))
    return chunks


# -------------------------
# Pipeline stages
# -------------------------

def collect_and_process() -> list[dict]:
    """
    Iterate over all source files, extract text, clean, chunk,
    and assemble metadata for each chunk.
    Returns a list of chunk records (as dict).
    """
    all_chunks: list[dict] = []
    for key, cfg in SOURCES.items():
        path = cfg["path"]
        doc_type = cfg["type"]
        if path.is_dir():
            files = []
            for ext in cfg.get("exts", []):
                files += list(path.glob(f"*{ext}"))
        elif path.is_file():
            files = [path]
        else:
            continue

        # CSV special handling
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, encoding="utf-8")
            for _, row in df.iterrows():
                text = (
                    f"{row['keyword']}: {row['definition']}. Example: {row['example']}"
                )
                for chunk in chunk_text(text):
                    all_chunks.append(
                        {
                            "id": str(uuid.uuid4()),
                            "source": key,
                            "url": f"csv://{path.name}",
                            "crawl_date": CRAWL_DATE,
                            "type": doc_type,
                            "text": chunk,
                        }
                    )
            continue

        # Other formats
        for p in files:
            extractor = {
                ".pdf": extract_pdf,
                ".docx": extract_docx,
                ".pptx": extract_pptx,
                ".md": lambda p: p.read_text(encoding="utf-8"),
                ".txt": lambda p: p.read_text(encoding="utf-8"),
            }.get(p.suffix.lower())
            if not extractor:
                continue

            raw = extractor(p)
            text = clean_text(raw)
            for chunk in chunk_text(text):
                all_chunks.append(
                    {
                        "id": str(uuid.uuid4()),
                        "source": key,
                        "url": f"file://{p.relative_to(DATA_DIR)}",
                        "crawl_date": CRAWL_DATE,
                        "type": doc_type,
                        "text": chunk,
                    }
                )
    return all_chunks


def save_chunks(chunks: list[dict], path: Path):
    """Serialize chunk list to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(chunks)} chunks to {path}")


def build_vector_store(chunks_file: Path, persist_dir: Path):
    """Load JSON chunks, create embeddings, and persist Chroma index."""
    with chunks_file.open("r", encoding="utf-8") as f:
        chunks = json.load(f)
    docs = [Document(page_content=c["text"], metadata=c) for c in chunks]
    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2") # Giải thích
    vectordb = Chroma.from_documents(
        docs, embedding=embedder, persist_directory=str(persist_dir)
    )
    vectordb.persist()
    print("Vector store built & persisted.")


# -------------------------
# Main pipeline entrypoint
# -------------------------
# if __name__ == "__main__":
#     chunks = collect_and_process()
#     save_chunks(chunks, DATA_DIR / "chunks.json")
#     build_vector_store(DATA_DIR / "chunks.json", DATA_DIR / "chroma_db")
