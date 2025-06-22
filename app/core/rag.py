import shutil
import logging
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.llms import Ollama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from langchain_openai import ChatOpenAI  # For DeepSeek API
from langchain.chains import RetrievalQA

from google.oauth2 import service_account

from app.core.config import settings
from data_pipeline import collect_and_process, save_chunks, build_vector_store
import torch
logger = logging.getLogger(__name__)

DATA_DIR    = Path("data")
CHUNKS_FILE = DATA_DIR / "chunks.json"
OLLAMA_DB   = Path("./chroma_db/ollama")
VERTEX_DB   = Path("./chroma_db/vertex")
DEEPSEEK_DB = Path("./chroma_db/deepseek")
KEY_DIR     = Path("./key")

device = 'cuda' if torch.cuda.is_available() else 'cpu'

pipelines = {
    "ollama": {"llm": None, "chain": None},
    "vertex": {"llm": None, "chain": None},
    "deepseek": {"llm": None, "chain": None},
}


def initialize_components():
    print("Initializing LLM & Embedding…")
    DATA_DIR.mkdir(exist_ok=True)

    # ------------ clean out stores ------------
    for db in (OLLAMA_DB, VERTEX_DB, DEEPSEEK_DB):
        if db.exists():
            shutil.rmtree(db)
            logger.info(f"Removed old vector store at {db}")

    # ------------ prepare chunks ------------
    if not CHUNKS_FILE.exists():
        chunks = collect_and_process()
        save_chunks(chunks, CHUNKS_FILE)

    # ------------ 1) Ollama + HF embeddings ------------
    try:
        # Use configurable Ollama settings with timeout and host
        llm_ollama = Ollama(
            model=settings.ollama_model,
            base_url=settings.ollama_host,
            timeout=settings.ollama_timeout
        )
        embed_hf = HuggingFaceEmbeddings(model_name=settings.hf_embedding_model)
        vs_ollama = build_vector_store(CHUNKS_FILE, OLLAMA_DB, embedding=embed_hf)
        retr_ollama = vs_ollama.as_retriever(search_kwargs={"k": 3})
        pipelines["ollama"]["llm"] = llm_ollama
        pipelines["ollama"]["chain"] = RetrievalQA.from_chain_type(
            llm=llm_ollama,
            chain_type="stuff",
            retriever=retr_ollama,
            return_source_documents=True,
        )
        logger.info(f"Ollama pipeline initialized with model: {settings.ollama_model}")
    except Exception as e:
        logger.error("Failed to initialize Ollama pipeline: %s", e, exc_info=True)
        pipelines["ollama"] = {"llm": None, "chain": None}

    # ------------ 2) DeepSeek pipeline ------------
    if settings.use_deepseek and settings.deepseek_api_key:
        try:
            llm_deepseek = ChatOpenAI(
                model=settings.deepseek_model,
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                temperature=0.7,
                max_tokens=2048,
            )
            embed_hf_deepseek = HuggingFaceEmbeddings(
                model_name=settings.hf_embedding_model,
                model_kwargs={'device': device}
            )
            vs_deepseek = build_vector_store(CHUNKS_FILE, DEEPSEEK_DB, embedding=embed_hf_deepseek)
            retr_deepseek = vs_deepseek.as_retriever(search_kwargs={"k": 3})
            pipelines["deepseek"]["llm"] = llm_deepseek
            pipelines["deepseek"]["chain"] = RetrievalQA.from_chain_type(
                llm=llm_deepseek,
                chain_type="stuff",
                retriever=retr_deepseek,
                return_source_documents=True,
            )
            logger.info(f"DeepSeek pipeline initialized with model: {settings.deepseek_model}")
        except Exception as e:
            logger.error("Failed to initialize DeepSeek pipeline: %s", e, exc_info=True)
            pipelines["deepseek"] = {"llm": None, "chain": None}
    else:
        logger.info("DeepSeek pipeline skipped (USE_DEEPSEEK=false or missing API key)")

    # ------------ 3) Gemini (Vertex) pipeline ------------
    if settings.use_vertex:
        try:
            load_dotenv()
            cred_file = KEY_DIR / settings.GOOGLE_APPLICATION_CREDENTIALS
            creds = service_account.Credentials.from_service_account_file(str(cred_file))
            print("Using Google credentials from:", cred_file.name)

            # === Option A: VertexAIEmbeddings with tuned batch_size & parallelism ===
            # embed_vert = VertexAIEmbeddings(
            #     project=settings.vertex_project,
            #     location=settings.vertex_location,
            #     model_name=settings.vertex_embedding_model,    # e.g. "gemini-pro"
            #     credentials=creds,
            #     request_parallelism=2,   # at most 2 parallel threads
            #     max_batch_size=50,       # start with up to 50 docs per request
            #     min_batch_size=5,        # back off down to 5 if needed
            # )

            # --- OR, Option B: use HuggingFaceEmbeddings for Vertex pipeline ---
            embed_vert = HuggingFaceEmbeddings(model_name=settings.hf_embedding_model, model_kwargs={'device': device})

            llm_vertex = ChatVertexAI(
                project=settings.vertex_project,
                location=settings.vertex_location,
                model_name=settings.vertex_llm_model,         # e.g. "gemini-pro"
                credentials=creds,
                temperature=0.7, 
            )
            vs_vertex = build_vector_store(CHUNKS_FILE, VERTEX_DB, embedding=embed_vert)
            retr_vertex = vs_vertex.as_retriever(search_kwargs={"k": 3})
            pipelines["vertex"]["llm"] = llm_vertex
            pipelines["vertex"]["chain"] = RetrievalQA.from_chain_type(
                llm=llm_vertex,
                chain_type="stuff",
                retriever=retr_vertex,
                return_source_documents=True,
            )
            logger.info("Vertex AI pipeline initialized successfully")

        except Exception as e:
            logger.error("Failed to initialize Vertex pipeline: %s", e, exc_info=True)
            pipelines["vertex"] = {"llm": None, "chain": None}
    else:
        logger.info("Vertex AI pipeline skipped (USE_VERTEX=false)")

    logger.info("All RAG pipelines are ready")
    print("RAG pipelines ready")
