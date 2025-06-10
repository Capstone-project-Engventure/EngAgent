# pip install fastapi uvicorn transformers torch sentencepiece
from fastapi import FastAPI, Request
from pydantic import BaseModel
from transformers import T5ForConditionalGeneration, T5Tokenizer

app = FastAPI()

model_name_1 = "vennify/t5-base-grammar-correction"
tokenizer = T5Tokenizer.from_pretrained(model_name_1)
model = T5ForConditionalGeneration.from_pretrained(model_name_1)

class TextRequest(BaseModel):
    content: str

@app.post("/correct")
def correct_text(request: TextRequest):
    input_text = "grammar: " + request.content
    input_ids = tokenizer.encode(input_text, return_tensors="pt", max_length=512, truncation=True)

    outputs = model.generate(input_ids, max_length=512, num_beams=4, early_stopping=True)
    corrected = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return {
        "original": request.content,
        "corrected": corrected
    }