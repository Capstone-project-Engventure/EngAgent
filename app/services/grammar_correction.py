from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from difflib import SequenceMatcher

# =============================
# ✅ Load the model
# =============================
MODEL_NAME = "vennify/t5-base-grammar-correction"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)


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


def correct_grammar(text: str):
    # Add the prefix "grammar: " to the input text for T5 model
    input_text = "grammar: " + text
    
    inputs = tokenizer(input_text, return_tensors="pt", truncation=True)
    outputs = model.generate(
        **inputs,
        max_length=256,
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
