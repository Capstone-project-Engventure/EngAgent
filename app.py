# FastAPI application with No RAG, Native RAG, and Agentic RAG routes
from fastapi import FastAPI, HTTPException
import os, json, time, re

from pathlib import Path
from pydantic import BaseModel
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.vectorstores import Chroma
from langchain.schema import Document

# from langchain_core.documents import Document


from langchain.document_loaders import TextLoader
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.tools import BaseTool

# import pipeline
from data_pipeline import collect_and_process, save_chunks, build_vector_store

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


# Setup Ollama and embeddings
llm = Ollama(model="mistral")
embedding = HuggingFaceEmbeddings()

# Setup ChromaDB
# db_path = "./chroma_db"
# data_dir = "./data"
# if not os.path.exists(db_path):
#     os.makedirs(db_path)

# all_docs = []


# def load_json_as_documents(filepath):
#     with open(filepath, "r", encoding="utf-8") as f:
#         data = json.load(f)
#     if isinstance(data, list):
#         return [
#             Document(page_content=json.dumps(entry), metadata={"source": filepath})
#             for entry in data
#         ]
#     else:
#         return [Document(page_content=json.dumps(data), metadata={"source": filepath})]


# Load documents
# for filename in os.listdir(data_dir):
#     file_path = os.path.join(data_dir, filename)
#     print(f"Processing file: {filename}")
#     if filename.endswith(".txt"):
#         loader = TextLoader(file_path)
#         docs = loader.load()
#     elif filename.endswith(".json"):
#         docs = load_json_as_documents(file_path)
#     else:
#         print(f"Skipping unsupported file: {filename}")
#         continue
#     try:
#         all_docs.extend(docs)
#         print(f"Loaded: {filename}")
#     except Exception as e:
#         print(f"Error loading {filename}: {e}")

if not CHUNKS.exists() or not DB_DIR.exists():
    print("🔄 Running data pipeline …")
    chunks = collect_and_process()
    save_chunks(chunks, CHUNKS)
    build_vector_store(CHUNKS, DB_DIR)

vectorstore = Chroma(persist_directory=str(DB_DIR), embedding_function=None)
retriever = vectorstore.as_retriever()
rag_chain = RetrievalQA.from_chain_type(
    llm=llm, chain_type="stuff", retriever=retriever
)

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


# Define Tools for Agentic RAG
class RAGTool(BaseTool):
    name: str = "RAG_Retriever"
    description: str = (
        "Retrieve relevant educational content from a vector database based on the query."
    )

    def _run(self, query: str) -> str:
        result = rag_chain({"query": query})
        return result["result"]

    def _arun(self, query: str):
        raise NotImplementedError("Async not supported")


class WebSearchTool(BaseTool):
    name: str = "Web_Search"
    description: str = (
        "Search the web for additional context or up-to-date information."
    )

    def _run(self, query: str) -> str:
        return (
            f"Web search results for '{query}': [Mock] Additional context from the web."
        )

    def _arun(self, query: str):
        raise NotImplementedError("Async not supported")


tools = [RAGTool(), WebSearchTool()]

# Initialize ReAct Agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
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
@app.post("/generate/native-rag")
async def generate_native_rag(request: ExerciseRequest):
    start_time = time.time()
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
        raise HTTPException(
            status_code=400,
            detail={"error": error, "raw": result, "duration_seconds": duration},
        )
    return parsed_json


# Route 3: Agentic RAG
@app.post("/generate/agentic-rag")
async def generate_agentic_rag(request: ExerciseRequest):
    start_time = time.time()
    query = f"""
    Generate an English learning exercise with the following details:
    - Skill: {request.skill}
    - Level: {request.level}
    - Topic: {request.topic}
    - Type: {request.type}
    Use the RAG_Retriever tool to fetch relevant context from the vector database.
    If the retrieved context is insufficient, use the Web_Search tool to gather additional information.
    Return the response in strict JSON format as specified by the prompt template.
    """
    result = agent.run(query)
    parsed_json, error = extract_clean_json(result)
    duration = time.time() - start_time

    if error:
        raise HTTPException(
            status_code=400,
            detail={"error": error, "raw": result, "duration_seconds": duration},
        )
    return parsed_json


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
