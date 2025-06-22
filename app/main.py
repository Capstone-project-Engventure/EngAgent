import uvicorn
from fastapi import FastAPI
from app.api.routers import exercise, prompt, grammar
from app.core.config import settings
from app.core.rag import initialize_components
# from app.core.rag import llm, embedding, vector_store, retriever, rag_chain
import app.core.rag as rag
import app.db.session as db
app = FastAPI(title="English Exercise Generator API")

@app.on_event("startup")
async def on_startup():
    initialize_components()
    await db.init_db()
    
@app.get("/health")
async def health_check():
    overall_ok = True
    components = {}

    # 1) Database
    db_status = await db.health_check_db()
    components["database"] = db_status
    if not db_status["ok"]:
        overall_ok = False

    # 2) RAG pipelines - now including DeepSeek
    for key in ("ollama", "vertex", "deepseek"):
        pipe = rag.pipelines.get(key, {})
        llm_ok    = pipe.get("llm")    is not None
        chain_ok  = pipe.get("chain")  is not None

        components[f"{key}_llm"] = {"ok": llm_ok}
        components[f"{key}_chain"] = {"ok": chain_ok}

        # Don't mark as failed if optional services are not configured
        if key == "vertex" and not settings.use_vertex:
            continue
        if key == "deepseek" and not settings.use_deepseek:
            continue
        
        # Only consider it a problem if the service should be available but isn't
        if key == "ollama" and (not llm_ok or not chain_ok):
            overall_ok = False

    # 3) Configuration status
    components["config"] = {
        "ollama_model": settings.ollama_model,
        "use_vertex": settings.use_vertex,
        "use_deepseek": settings.use_deepseek,
        "deepseek_configured": bool(settings.deepseek_api_key)
    }

    status = "healthy" if overall_ok else "degraded"
    return {"status": status, "components": components}

# 2. Gắn các router
app.include_router(exercise.router, prefix="/api/exercises", tags=["exercise"])
app.include_router(prompt.router, prefix="/api/prompts", tags=["prompt"])
app.include_router(grammar.router, prefix="/api/grammar", tags=["grammar"])

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
