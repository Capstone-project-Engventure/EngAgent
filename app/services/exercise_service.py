import json, re, time, string
import logging
from fastapi import HTTPException

from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from langchain_community.llms import Ollama
from langchain.chains import RetrievalQA

from app.core.config import settings
import app.core.rag as rag
# from app.core.prompts import get_prompt_template
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def clean_llm_response(text: str) -> str:
    """Clean and sanitize LLM response to extract pure JSON."""
    if not text:
        raise ValueError("Empty response from LLM")
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove markdown code blocks
    # Pattern matches: ```json\n...``` or ```\n...```
    text = re.sub(r'^```(?:json)?\s*\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n```\s*$', '', text, flags=re.MULTILINE)
    
    # Remove any remaining ``` at start/end
    if text.startswith('```'):
        text = text[3:].strip()
    if text.endswith('```'):
        text = text[:-3].strip()
    
    # Ensure it starts and ends with array brackets
    if not text.startswith('['):
        # Try to find JSON array in the response
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
        else:
            raise ValueError("No JSON array found in response")
    
    return text


# def validate_mcq_exercise(exercise: dict) -> bool:
#     """
#     Validate MCQ exercise:
#     - 'options' must be a list with >= 2 elements
#     - Each element must be a dict containing:
#         * 'key': a string and one uppercase letter from A to Z
#         * 'option': a non-empty string
#     """
#     allowed_keys = set(string.ascii_uppercase)
#     options = exercise.get("options")

#     # 1. Check that options exists and is a list
#     if not isinstance(options, list):
#         logger.error("Invalid or missing 'options': %r", options)
#         return False

#     # 2. Check that there are at least 2 options
#     if len(options) < 2:
#         logger.warning("Not enough options: only %d provided", len(options))
#         return False

#     # 3. Validate each option entry
#     seen_keys = set()
#     for idx, opt in enumerate(options, start=1):
#         if not isinstance(opt, dict):
#             logger.error("Option #%d is not a dict: %r", idx, opt)
#             return False

#         key = opt.get("key")
#         value = opt.get("option")

#         # 3a. Validate 'key'
#         if not isinstance(key, str):
#             logger.error("Option #%d has a non-string key: %r", idx, key)
#             return False
#         if key not in allowed_keys:
#             logger.error(
#                 "Invalid key at option #%d: %r (must be one uppercase letter A-Z)",
#                 idx, key
#             )
#             return False
#         if key in seen_keys:
#             logger.error("Duplicate key at option #%d: %r", idx, key)
#             return False
#         seen_keys.add(key)

#         # 3b. Validate 'option' value
#         if not isinstance(value, str) or not value.strip():
#             logger.error(
#                 "Invalid 'option' for key %r: %r (must be a non-empty string)",
#                 key, value
#             )
#             return False

#     logger.info("Options validation passed: %d valid options", len(options))
#     return True

def validate_mcq_exercise(exercise: dict) -> bool:
    """
    Validate or normalize MCQ exercise:
    - If options is a JSON-encoded list of strings, convert to list of dicts {key, option}
    - If options is a dict mapping keys to string values, convert to list of dicts
    - 'options' must be a list with >= 2 elements
    - Each element must be a dict containing:
        * 'key': a string uppercase letter
        * 'option': a non-empty string
    """
    allowed_keys = set(string.ascii_uppercase)
    options = exercise.get("options")

    # 1. Parse if options is a JSON string
    if isinstance(options, str):
        try:
            options = json.loads(options)
        except json.JSONDecodeError:
            logger.error("Options string is not valid JSON: %r", options)
            return False

    # 2. Convert list of strings to list of dicts
    if isinstance(options, list) and options and all(isinstance(o, str) for o in options):
        converted = []
        for idx, text in enumerate(options):
            if idx >= len(string.ascii_uppercase):
                logger.error("Too many options to assign keys: %d", len(options))
                return False
            key = string.ascii_uppercase[idx]
            converted.append({"key": key, "option": text})
        options = converted
        exercise["options"] = options

    # 3. Convert dict mapping keys to values into list of dicts
    if isinstance(options, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in options.items()):
        converted = []
        for k, v in options.items():
            converted.append({"key": k, "option": v})
        options = converted
        exercise["options"] = options

    # 4. Validate that options is now a list
    if not isinstance(options, list):
        logger.error("Invalid or missing 'options': %r", options)
        return False

    # 5. Check minimum count
    if len(options) < 2:
        logger.warning("Not enough options: only %d provided", len(options))
        return False

    # 6. Validate each option entry
    seen_keys = set()
    for idx, opt in enumerate(options, start=1):
        if not isinstance(opt, dict):
            logger.error("Option #%d is not a dict: %r", idx, opt)
            return False

        key = opt.get("key")
        value = opt.get("option")

        # Validate 'key'
        if not isinstance(key, str) or key not in allowed_keys:
            logger.error("Invalid key at option #%d: %r (must be one uppercase letter A-Z)", idx, key)
            return False
        if key in seen_keys:
            logger.error("Duplicate key at option #%d: %r", idx, key)
            return False
        seen_keys.add(key)

        # Validate 'option'
        if not isinstance(value, str) or not value.strip():
            logger.error("Invalid 'option' for key %r: %r (must be non-empty string)", key, value)
            return False

    logger.info("Options validation passed: %d valid options", len(options))
    return True

def validate_exercises_array(exercises: List[Dict[str, Any]], expected_count: int, expected_type: str) -> bool:
    """Validate the entire exercises array."""
    if len(exercises) != expected_count:
        logger.warning(f"Expected {expected_count} exercises, got {len(exercises)}")
        return False
    
    for i, exercise in enumerate(exercises):
        if not validate_mcq_exercise(exercise):
            logger.warning(f"Exercise {i} failed validation")
            return False
    
    return True


def extract_clean_json(text: str):
    match = re.search(r"{.*}", text, re.DOTALL)
    if not match:
        raise ValueError("Không tìm thấy JSON trong response")
    return json.loads(match.group(0))


# async def _generate_exercise(llm, prompt: str) -> Dict[str, Any]:
#     start = time.time()
#     try:
#         raw = llm.invoke(prompt)
#     except Exception as e:
#         logger.error("Error khi gọi LLM: %s", e, exc_info=True)
#         raise HTTPException(status_code=502, detail="LLM service error")

#     # lấy text trả về
#     text = getattr(raw, "content", str(raw))

#     try:
#         cleaned_text = clean_llm_response(text)
#         logger.debug(f"Cleaned response: {cleaned_text[:500]}...")
#     except ValueError as e:
#         logger.warning(f"Attempt {attempt + 1} - Failed to clean response: {e}")    

#     try:
#         parsed = json.loads(text)
#     except (ValueError, json.JSONDecodeError) as e:
#         logger.error("Failed to parse JSON từ LLM response: %s\nRaw: %s", e, text, exc_info=True)
#         raise HTTPException(status_code=500, detail="Invalid JSON format from LLM")

#     # Nếu LLM trả về list, gói nó vào key "exercises"
#     exercises = parsed if isinstance(parsed, list) else parsed.get("exercises", parsed)
#     return {
#         "exercises": exercises,
#         "duration_seconds": time.time() - start,
#     }

async def _generate_exercise(llm, prompt: str, expected_count: int = 1, expected_type: str = 'mcq') -> Dict[str, Any]:
    """Enhanced exercise generation with robust validation."""
    start = time.time()
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Generate response
            raw = llm.invoke(prompt)
            text = getattr(raw, "content", str(raw))
            
            logger.info(f"Attempt {attempt + 1} - Raw LLM response length: {len(text)}")
            logger.debug(f"Raw response: {text[:500]}...")  # Log first 500 chars
            
            # Clean response
            try:
                cleaned_text = clean_llm_response(text)
                logger.debug(f"Cleaned response: {cleaned_text[:500]}...")
            except ValueError as e:
                logger.warning(f"Attempt {attempt + 1} - Failed to clean response: {e}")
                if attempt == max_retries - 1:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to extract valid JSON from LLM response after {max_retries} attempts"
                    )
                continue
            
            # Parse JSON
            try:
                parsed = json.loads(cleaned_text)
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Attempt {attempt + 1} - JSON parse error: {e}")
                logger.debug(f"Failed JSON text: {cleaned_text}")
                if attempt == max_retries - 1:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Invalid JSON format from LLM after {max_retries} attempts"
                    )
                continue
            
            # Ensure we have a list
            if isinstance(parsed, dict):
                exercises = parsed.get("exercises", [parsed])
            elif isinstance(parsed, list):
                exercises = parsed
            else:
                logger.warning(f"Attempt {attempt + 1} - Unexpected response format: {type(parsed)}")
                if attempt == max_retries - 1:
                    raise HTTPException(status_code=500, detail="Unexpected response format from LLM")
                continue
            
            # Validate structure
            if not validate_exercises_array(exercises, expected_count, expected_type):
                logger.warning(f"Attempt {attempt + 1} - Validation failed")
                if attempt == max_retries - 1:
                    # Return partially valid data with warning
                    logger.error("All attempts failed validation, returning partial data")
                    return {
                        "exercises": exercises,  # Return what we have
                        "duration_seconds": time.time() - start,
                        "validation_warnings": ["Some exercises may not meet quality standards"]
                    }
                continue
            
            # Success!
            logger.info(f"Successfully generated {len(exercises)} exercises on attempt {attempt + 1}")
            return {
                "exercises": exercises,
                "duration_seconds": time.time() - start,
                "attempt_count": attempt + 1
            }
            
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} - Unexpected error: {e}", exc_info=True)
            if attempt == max_retries - 1:
                raise HTTPException(status_code=502, detail="LLM service error after multiple attempts")
            continue
    
    # This should never be reached due to the raises above, but just in case
    raise HTTPException(status_code=500, detail="Failed to generate exercises after all attempts")