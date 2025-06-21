from fastapi import APIRouter, HTTPException, Request
from app.services.grammar_correction import correct_grammar
from pydantic import BaseModel

router = APIRouter()

class GrammarRequest(BaseModel):
    text: str

@router.post("/check")
async def check_grammar(request: GrammarRequest):
    try:
        corrected_text = correct_grammar(request.text)
        return {"corrected_text": corrected_text}
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred during grammar correction.")
