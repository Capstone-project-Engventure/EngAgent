# from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
# import torch
# from difflib import SequenceMatcher
# from fastapi import FastAPI, Request
# import uvicorn
# import nest_asyncio
# from pyngrok import ngrok

# # Load the grammar correction model
# tokenizer = AutoTokenizer.from_pretrained("vennify/t5-base-grammar-correction")
# model = AutoModelForSeq2SeqLM.from_pretrained("vennify/t5-base-grammar-correction")


# def explain_error(error):
#     if error['type'] == 'replace':
#         return f"'{error['orig']}' should be replaced with '{error['corrected']}' to correct grammar or word choice."
#     elif error['type'] == 'delete':
#         return f"'{error['orig']}' is unnecessary and should be removed."
#     elif error['type'] == 'insert':
#         return f"Missing '{error['corrected']}' in the sentence."
#     return "Unclear error type."

# def analyze_errors(orig: str, corrected: str):
#     matcher = SequenceMatcher(None, orig.split(), corrected.split())
#     errors = []
#     for tag, i1, i2, j1, j2 in matcher.get_opcodes():
#         if tag != 'equal':
#             orig_seg = " ".join(orig.split()[i1:i2])
#             corr_seg = " ".join(corrected.split()[j1:j2])
#             error = {
#                 'type': tag,
#                 'orig': orig_seg,
#                 'corrected': corr_seg,
#                 'explanation': explain_error({'type': tag, 'orig': orig_seg, 'corrected': corr_seg})
#             }
#             errors.append(error)
#     return errors, len(errors)

# def analyze_errors(orig: str, corrected: str):
#     matcher = SequenceMatcher(None, orig.split(), corrected.split())
#     errors = []
#     for tag, i1, i2, j1, j2 in matcher.get_opcodes():
#         if tag != 'equal':
#             orig_seg = " ".join(orig.split()[i1:i2])
#             corr_seg = " ".join(corrected.split()[j1:j2])
#             error = {
#                 'type': tag,
#                 'orig': orig_seg,
#                 'corrected': corr_seg,
#                 'explanation': explain_error({
#                     'type': tag,
#                     'orig': orig_seg,
#                     'corrected': corr_seg
#                 })
#             }
#             errors.append(error)
#     return errors, len(errors)

# # Simple scoring: 10 minus number of errors (floor at 0)
# def score_essay(num_errors: int):
#     return max(10 - num_errors, 0)

# def correct_and_evaluate(text: str):
#     inputs = tokenizer(text, return_tensors='pt')
#     outputs = model.generate(**inputs)
#     corrected = tokenizer.decode(outputs[0], skip_special_tokens=True)
#     note_list, num_errors = analyze_errors(text, corrected)
#     score = score_essay(num_errors)

#     # summary = f"You made {num_errors} grammar mistake{'s' if num_errors != 1 else ''}."
#     # if num_errors == 0:
#     #     summary += " Excellent!"
#     # elif any(e['type'] == 'replace' and "tense" in e['explanation'] for e in errors):
#     #     summary += " Focus on correct verb tense."

#     response = {
#         "original": text,
#         'corrected': corrected,
#         'note': note_list,
#         'score': score,
#         #  "summary": summary
#     }
#     return response

# ngrok.set_auth_token("2oClTLViDar0ydFfuK4ctaoJtuz_6TT9L2to9xShTnRm1sNXY")
# app = FastAPI()

# @app.post("/correct")
# async def correct_endpoint(request: Request):
#     data = await request.json()
#     text = data.get('text', '')
#     result = correct_and_evaluate(text)
#     return result

# # Expose to internet via ngrok
# public_url = ngrok.connect(8001)
# print(f"Public URL: {public_url}")

# nest_asyncio.apply()
# uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


from fastapi import FastAPI, Request
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import torch
from difflib import SequenceMatcher
import nest_asyncio
from pyngrok import ngrok, conf, exception
import uvicorn
import threading
from fastapi.middleware.cors import CORSMiddleware

# =============================
# ✅ Load the model
# =============================
MODEL_NAME = "vennify/t5-base-grammar-correction"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)


# =============================
# ✅ Error analysis helpers
# =============================
def explain_error(error):
    if error["type"] == "replace":
        return f"'{error['orig']}' should be replaced with '{error['corrected']}' to use the correct form or tense."
    elif error["type"] == "insert":
        return (
            f"'{error['corrected']}' should be inserted for grammatical completeness."
        )
    elif error["type"] == "delete":
        return f"'{error['orig']}' should be removed as it's unnecessary."
    return "General grammatical correction."


def analyze_errors(orig: str, corrected: str):
    orig_words = orig.split()
    corrected_words = corrected.split()
    matcher = SequenceMatcher(None, orig_words, corrected_words)
    errors = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            error = {
                "type": tag,
                "orig": " ".join(orig_words[i1:i2]),
                "corrected": " ".join(corrected_words[j1:j2]),
            }
            error["explanation"] = explain_error(error)
            errors.append(error)
    return errors, len(errors)


def score_essay(num_errors: int):
    return max(10 - num_errors, 0)


def correct_and_evaluate(text: str):
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    outputs = model.generate(
        **inputs,
        max_length=256,  # tránh bị cắt cụt nội dung
        num_beams=4,
        early_stopping=True,
    )
    corrected = tokenizer.decode(outputs[0], skip_special_tokens=True)

    errors, num_errors = analyze_errors(text, corrected)
    score = score_essay(num_errors)

    summary = f"You made {num_errors} grammar mistake{'s' if num_errors != 1 else ''}."
    if num_errors == 0:
        summary += " Excellent!"
    elif any("tense" in e["explanation"] for e in errors):
        summary += " Focus on correct verb tense."

    return {
        "original": text,
        "corrected": corrected,
        "score": score,
        "errors": errors,
        "summary": summary,
    }


# # =============================
# # ✅ FastAPI app setup
# # =============================
# app = FastAPI()
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # bạn có thể giới hạn origin ở đây
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


@app.post("/correct")
async def correct_endpoint(request: Request):
    data = await request.json()
    text = data.get("text", "")
    result = correct_and_evaluate(text)
    return result


# =============================
# ✅ Uvicorn + Ngrok startup
# =============================
def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")


def start_ngrok():
    try:
        conf.get_default().auth_token = (
            "2yb9t6brSw4m6V0ahHIsiRfmxyl_cnxzv7tqvJzNoPQfBJvC"  # update nếu cần
        )
        public_url = ngrok.connect(8001)
        print(f"🚀 Ngrok tunnel available at: {public_url}")
    except exception.PyngrokNgrokError as e:
        print("⚠️ Ngrok failed to start. Possible cause: limit reached.")
        print("ℹ️  Visit https://dashboard.ngrok.com/agents to manage sessions.")
        print(str(e))


if __name__ == "_main_":
    nest_asyncio.apply()
    threading.Thread(target=run_server).start()
    start_ngrok()