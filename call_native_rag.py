"""
Utility script to hit the native-rag endpoint multiple times and persist all returned exercises

Usage:
    python call_native_rag.py

Prerequisites:
    pip install requests
"""

import json
import random
import time
from pathlib import Path
from typing import List

import requests

# ---------------------------- Configuration ----------------------------- #
BASE_URL = "http://localhost:8000/api/exercises/native-rag?useVertex=true"
CALLS: int = 20                 # Maximum number of API calls
EXERCISES_PER_CALL: int = 5     # `number` payload field
OUTPUT_FILE = Path("all_exercises.json")
REQUEST_TIMEOUT = 120           # seconds

# Pools to randomise request parameters
SKILLS: List[str] = [
    "grammar",
    "vocabulary",
    "reading",
    "listening",
    "writing",
]
LEVELS: List[str] = ["A1", "A2", "B1", "B2", "C1", "C2"]
TOPICS: List[str] = [
    "present perfect tense",
    "phrasal verbs",
    "passive voice",
    "conditional sentences",
    "reported speech",
    "future tenses",
    "modal verbs",
    "comparatives and superlatives",
    "quantifiers",
    "articles",
]

# ---------------------------- Helper functions -------------------------- #

def build_payload() -> dict:
    """Construct a request body with randomised skill, level, and topic."""
    skill = random.choice(SKILLS)
    level = random.choice(LEVELS)
    topic = random.choice(TOPICS)

    return {
        "number": EXERCISES_PER_CALL,
        "name": f"English {skill.title()} Exercise",
        "skill": skill,
        "level": level,
        "topic": topic,
        "type": "mcq",
        "use_few_shot": False,
        "few_shot_examples": [],
        "model_name": "Gemini",
        "prompt_name": "english_exercise_default",
    }


def call_api(payload: dict) -> List[dict]:
    """Send POST request and return list of exercises (may be empty)."""
    response = requests.post(BASE_URL, json=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    data = response.json()
    exercises = data.get("exercises", [])
    if not isinstance(exercises, list):
        raise ValueError("Response JSON is missing 'exercises' list")
    return exercises


# ---------------------------- Main routine ------------------------------ #

def main():
    all_exercises: List[dict] = []

    for i in range(1, CALLS + 1):
        payload = build_payload()
        try:
            t0 = time.time()
            exercises = call_api(payload)
            elapsed = time.time() - t0
            all_exercises.extend(exercises)
            print(
                f"Call {i}/{CALLS}: obtained {len(exercises):2d} exercises "
                f"(total collected: {len(all_exercises)}) in {elapsed:.2f}s."
            )
        except Exception as err:
            print(f"Call {i} failed: {err}")

    # Persist results
    OUTPUT_FILE.write_text(json.dumps(all_exercises, indent=2, ensure_ascii=False))
    print(f"\nSaved {len(all_exercises)} exercises to '{OUTPUT_FILE.resolve()}'")


if __name__ == "__main__":
    main() 