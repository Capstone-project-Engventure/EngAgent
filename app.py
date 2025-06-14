# FastAPI application with No RAG, Native RAG, and Agentic RAG routes
from fastapi import FastAPI, HTTPException
import os, json, time, re, shutil

from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import logging

# Updated imports for modern LangChain
try:
    from langchain_community.llms import Ollama
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.chains import RetrievalQA
    from langchain.prompts import PromptTemplate
    from langchain.schema import Document
    from langchain.document_loaders import TextLoader
    from langchain.agents import initialize_agent, Tool, AgentType
    from langchain.tools import BaseTool
except ImportError as e:
    logging.error(f"LangChain import error: {e}")
    raise

# Try to import pipeline with error handling
try:
    from data_pipeline import collect_and_process, save_chunks, build_vector_store, SOURCES
except ImportError as e:
    logging.error(f"Data pipeline import error: {e}")
    # Create mock functions or raise appropriate error
    raise HTTPException(
        status_code=500, 
        detail="Data pipeline module not available. Please ensure data_pipeline.py exists."
    )

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="English Exercise Generator API")

# Thiết lập paths
DATA_DIR = Path("data")
CHUNKS = DATA_DIR / "chunks.json"
DB_DIR = Path("./chroma_db")


# Pydantic model for request validation
class ExerciseRequest(BaseModel):
    name: str = "Exercise"
    skill: str
    level: str
    topic: str
    type: str

class SourceIn(BaseModel):
    type: str
    path: str
    exts: Optional[List[str]] = None

class PromptTemplateIn(BaseModel):
    template: str
    input_variables: List[str]

# Initialize global variables
vector_store = None
retriever = None
rag_chain = None
llm = None
embedding = None

# Initialize components with error handling
def initialize_components():
    global llm, embedding
    try:
        llm = Ollama(model="mistral")
        embedding = HuggingFaceEmbeddings()
        logger.info("LLM and embedding models initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        raise


# Prompt template
prompt_template = PromptTemplate(
    input_variables=["skill", "level", "topic", "type", "name", "context"],
    template="""
You are an educational content generator. Your task is to return a **valid JSON object only**.
Requirements:
    - Do NOT include any markdown syntax like ```json
    - Do NOT add explanation or description outside the JSON
    - Use the provided context to enhance the exercise if available
    - If the type is not mcq, leave the options field empty

Generate 1 English learning exercise in JSON with the following metadata:
- Name: {name}
- Skill: {skill}
- Level: {level}
- Topic: {topic}
- Type: {type}
Return strictly formatted JSON like:
{{
  "name": "{name}",
  "question": "Question text",
  "system_answer": null,
  "type": "{type}",
  "level": "{level}",
  "skill": "{skill}",
  "lesson": "lesson_id",
  "generated_by": "mistral_model",
  "description": "Instruction",
  "options": {{
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "..."
  }} || []
}}
Context: {context}
""",
)




# Utility function to extract JSON
def extract_clean_json(text):
    match = re.search(r"{.*}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0)), None
        except json.JSONDecodeError as e:
            return None, f"JSON decode error: {e}"
    return None, "No valid JSON found in the response"

@app.on_event("startup")
async def init_pipeline():
    global vector_store, retriever, rag_chain
    
    try:
        # Initialize components first
        initialize_components()
        
        # Create data directory if it doesn't exist
        DATA_DIR.mkdir(exist_ok=True)
        
        # Clean up existing vector store
        if DB_DIR.exists():
            shutil.rmtree(DB_DIR)
            logger.info("Cleaned up existing vector store")
        
        # Build or load vector store
        if not CHUNKS.exists():
            logger.info("Building new vector store...")
            chunks = collect_and_process()
            save_chunks(chunks, CHUNKS)
            vector_store = build_vector_store(CHUNKS, DB_DIR)
        else:
            logger.info("Loading existing vector store...")
            vector_store = build_vector_store(CHUNKS, DB_DIR)
        
        if vector_store is None:
            raise ValueError("Failed to create vector store")
        
        # Initialize retriever and RAG chain
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        rag_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        
        logger.info("RAG pipeline initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize RAG pipeline: {str(e)}"
        )

# Route 1: No RAG
@app.post("/generate/no-rag")
async def generate_no_rag(request: ExerciseRequest):
    start_time = time.time()
    result = llm(
        prompt_template.format(
            name=request.name,
            skill=request.skill,
            level=request.level,
            topic=request.topic,
            type=request.type,
            context="No context provided",
        )
    )
    parsed_json, error = extract_clean_json(result)
    duration = time.time() - start_time

    if error:
        raise HTTPException(
            status_code=400,
            detail={"error": error, "raw": result, "duration_seconds": duration},
        )
    return parsed_json


# Route 2: Native RAG
@app.post("/api/exercises/native-rag")
async def generate_native_rag(request: ExerciseRequest):
    if rag_chain is None:
        raise HTTPException(
            status_code=503,
            detail="RAG chain not initialized. Please restart the server."
        )
    start_time = time.time()
    try:
        query = f"Generate an English learning exercise for skill: {request.skill}, level: {request.level}, topic: {request.topic}, type: {request.type}"
        context = rag_chain({"query": query})["result"]
        result = llm(
            prompt_template.format(
                name=request.name,
                skill=request.skill,
                level=request.level,
                topic=request.topic,
                type=request.type,
                context=context,
            )
        )
        parsed_json, error = extract_clean_json(result)
        duration = time.time() - start_time

        if error:
                logger.error(f"JSON parsing error: {error}")
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": error, 
                        "raw": result[:500] + "..." if len(result) > 500 else result,
                        "duration_seconds": duration
                    },
                )
            
        # Add metadata
        parsed_json["duration_seconds"] = duration
        parsed_json["context_length"] = len(context)
        
        return parsed_json
        
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Unexpected error in native-rag: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Internal server error: {str(e)}",
                "duration_seconds": duration
            }
        )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "components": {
            "llm": llm is not None,
            "embedding": embedding is not None,
            "vector_store": vector_store is not None,
            "retriever": retriever is not None,
            "rag_chain": rag_chain is not None
        }
    }
    

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)



# Define Tools for Agentic RAG
# class RAGTool(BaseTool):
#     name: str = "RAG_Retriever"
#     description: str = (
#         "Retrieve relevant educational content from a vector database based on the query."
#     )

#     def _run(self, query: str) -> str:
#         result = rag_chain({"query": query})
#         return result["result"]

#     def _arun(self, query: str):
#         raise NotImplementedError("Async not supported")


# class WebSearchTool(BaseTool):
#     name: str = "Web_Search"
#     description: str = (
#         "Search the web for additional context or up-to-date information."
#     )

#     def _run(self, query: str) -> str:
#         return (
#             f"Web search results for '{query}': [Mock] Additional context from the web."
#         )

#     def _arun(self, query: str):
#         raise NotImplementedError("Async not supported")


# tools = [RAGTool(), WebSearchTool()]

# Initialize ReAct Agent
# agent = initialize_agent(
#     tools=tools,
#     llm=llm,
#     agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
#     verbose=True,
# )

# # Route 3: Agentic RAG
# @app.post("/generate/agentic-rag")
# async def generate_agentic_rag(request: ExerciseRequest):
#     start_time = time.time()
#     query = f"""
#     Generate an English learning exercise with the following details:
#     - Skill: {request.skill}
#     - Level: {request.level}
#     - Topic: {request.topic}
#     - Type: {request.type}
#     Use the RAG_Retriever tool to fetch relevant context from the vector database.
#     If the retrieved context is insufficient, use the Web_Search tool to gather additional information.
#     Return the response in strict JSON format as specified by the prompt template.
#     """
#     result = agent.run(query)
#     parsed_json, error = extract_clean_json(result)
#     duration = time.time() - start_time

#     if error:
#         raise HTTPException(
#             status_code=400,
#             detail={"error": error, "raw": result, "duration_seconds": duration},
#         )
#     return parsed_json


# # --- Read all sources ---
# @app.get("/sources")
# async def list_sources():
#     return {
#         name: {
#             "type": cfg["type"],
#             "path": str(cfg["path"]),
#             **({"exts": cfg["exts"]} if "exts" in cfg else {})
#         }
#         for name, cfg in SOURCES.items()
#     }

# # --- Read one source ---
# @app.get("/sources/{name}")
# async def get_source(name: str):
#     if name not in SOURCES:
#         raise HTTPException(404, f"Source '{name}' not found")
#     cfg = SOURCES[name]
#     return {
#         "type": cfg["type"],
#         "path": str(cfg["path"]),
#         **({"exts": cfg["exts"]} if "exts" in cfg else {})
#     }

# # --- Create new source ---
# @app.post("/sources", status_code=201)
# async def create_source(name: str, payload: SourceIn):
#     if name in SOURCES:
#         raise HTTPException(400, f"Source '{name}' already exists")
#     SOURCES[name] = {
#         "type": payload.type,
#         "path": Path(payload.path),
#         **({"exts": payload.exts} if payload.exts else {})
#     }
#     return {"message": f"Source '{name}' created"}

# # --- Update existing source ---
# @app.put("/sources/{name}")
# async def update_source(name: str, payload: SourceIn):
#     if name not in SOURCES:
#         raise HTTPException(404, f"Source '{name}' not found")
#     SOURCES[name].update({
#         "type": payload.type,
#         "path": Path(payload.path),
#         **({"exts": payload.exts} if payload.exts else {})
#     })
#     return {"message": f"Source '{name}' updated"}

# # --- Delete source ---
# @app.delete("/sources/{name}")
# async def delete_source(name: str):
#     if name not in SOURCES:
#         raise HTTPException(404, f"Source '{name}' not found")
#     del SOURCES[name]
#     return {"message": f"Source '{name}' deleted"}

# from langchain.prompts import PromptTemplate

# # GET hiện tại
# @app.get("/prompt-template")
# async def read_prompt_template():
#     return {
#         "template": prompt_template.template,
#         "input_variables": prompt_template.input_variables
#     }

# # PUT để cập nhật
# @app.put("/prompt-template")
# async def update_prompt_template(payload: PromptTemplateIn):
#     global prompt_template
#     prompt_template = PromptTemplate(
#         input_variables=payload.input_variables,
#         template=payload.template
#     )
#     return {
#         "message": "Prompt template updated",
#         "template": prompt_template.template,
#         "input_variables": prompt_template.input_variables
#     }
    
