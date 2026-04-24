"""
Task 1 evaluator — uploads chart image to DO Spaces, calls Gemini 2.5 Flash
with the image + essay, parses structured JSON scores and feedback.
"""

import hashlib
import json
import re
import logging
from typing import Optional

import google.generativeai as genai
from django.core.cache import cache

from .gemini_pool import get_flash_pool, AllKeysExhaustedError

logger = logging.getLogger(__name__)

# Cache TTL: 2 hours
CACHE_TTL = 7200

# IELTS Task 1 evaluation prompt
TASK1_PROMPT = """You are an expert IELTS examiner specializing in marking Writing Task 1 responses.

You are given:
1. A chart/graph/diagram image.
2. A candidate's written response.

Evaluate the response on these 4 official criteria (1.0–9.0 scale, 0.5 increments):
- Task Achievement: Clear overview, key features highlighted.
- Coherence and Cohesion: Logical organization, clear progression.
- Lexical Resource: Vocabulary range and accuracy.
- Grammatical Range and Accuracy: Sentence variety and grammatical precision.

You MUST output ONLY a raw JSON object. Do NOT include markdown blocks, code fences (```json), or any preamble/postscript. 

Use EXACTLY these key names:
{{
  "scores": {{
    "task_response": <number 1.0-9.0>,
    "coherence": <number 1.0-9.0>,
    "lexical": <number 1.0-9.0>,
    "grammar": <number 1.0-9.0>,
    "overall": <mean of the four scores rounded to nearest 0.5>
  }},
  "feedback": {{
    "task_response": "<2-4 sentences of helpful, professional feedback>",
    "coherence": "<2-4 sentences of helpful, professional feedback>",
    "lexical": "<2-4 sentences of helpful, professional feedback>",
    "grammar": "<2-4 sentences of helpful, professional feedback>",
    "improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>", "<improvement 4>"]
  }}
}}

Task Question/Prompt:
\"\"\"
{task_question}
\"\"\"

Candidate's essay:
{essay}
"""


def _cache_key(image_url: str, essay: str, task_question: str | None = None) -> str:
    """Generate a stable cache key from image URL + essay + question hash."""
    content = f"{image_url}::{essay}::{task_question or ''}"
    return f"task1_eval:{hashlib.sha256(content.encode()).hexdigest()}"


def _normalize_keys(data: dict) -> dict:
    """
    Normalize Gemini response keys to match the expected schema.
    Safely separates scores (numeric) and feedback (text) into their own dicts.
    """
    SCORE_KEY_MAP = {
        "coherence_and_cohesion": "coherence",
        "grammatical_range_and_accuracy": "grammar",
        "grammatical_range": "grammar",
        "task_achievement": "task_response",
        "lexical_resource": "lexical",
        "overall_score": "overall",
        "overall_band": "overall",
    }

    def remap_keys(obj: dict) -> dict:
        """Recursively remap keys in a dict using SCORE_KEY_MAP."""
        result = {}
        for k, v in obj.items():
            clean_k = k.lower().replace(" ", "_").replace("-", "_")
            new_key = SCORE_KEY_MAP.get(clean_k, clean_k)
            result[new_key] = remap_keys(v) if isinstance(v, dict) else v
        return result

    remapped = remap_keys(data)

    # ── Extract scores sub-dict ──────────────────────────────────────────────
    # Look for a nested 'scores' block first; fall back to root-level numbers.
    raw_scores = remapped.get("scores", {})
    if not isinstance(raw_scores, dict):
        raw_scores = {}

    SCORE_KEYS = ["task_response", "coherence", "lexical", "grammar", "overall"]
    scores = {}
    for key in SCORE_KEYS:
        val = raw_scores.get(key)
        if val is None:
            root_val = remapped.get(key)
            if isinstance(root_val, (int, float)):
                val = root_val
        try:
            scores[key] = float(val) if val is not None else 0.0
        except (ValueError, TypeError):
            scores[key] = 0.0

    # ── Extract feedback sub-dict ────────────────────────────────────────────
    raw_feedback = remapped.get("feedback", {})
    if not isinstance(raw_feedback, dict):
        raw_feedback = {}

    FEEDBACK_KEYS = ["task_response", "coherence", "lexical", "grammar"]
    feedback = {}
    for key in FEEDBACK_KEYS:
        val = raw_feedback.get(key)
        if val is None:
            root_val = remapped.get(key)
            if isinstance(root_val, str):
                val = root_val
        feedback[key] = val or ""

    feedback["improvements"] = raw_feedback.get(
        "improvements", remapped.get("improvements", [])
    )
    if not isinstance(feedback["improvements"], list):
        feedback["improvements"] = []

    return {"scores": scores, "feedback": feedback}


def _parse_json_response(text: str) -> dict:
    """
    Robustly parse a JSON response from Gemini.
    Handles: markdown fences (matched or unclosed), trailing commas,
    key normalization, and truncated responses.
    """
    text = text.strip()

    # 1. Strip markdown fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        # Handle unclosed fence (response truncated before closing ```)
        unclosed = re.match(r'^```(?:json)?\s*([\s\S]+)', text)
        if unclosed:
            text = unclosed.group(1).strip()

    # 2. Try direct parse
    try:
        return _normalize_keys(json.loads(text))
    except json.JSONDecodeError:
        pass

    # 3. Strip trailing commas then retry
    cleaned = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return _normalize_keys(json.loads(cleaned))
    except json.JSONDecodeError:
        pass

    # 4. Extract first balanced JSON object
    obj_match = re.search(r'(\{[\s\S]*\})', cleaned)
    if obj_match:
        try:
            return _normalize_keys(json.loads(obj_match.group(1)))
        except json.JSONDecodeError as e:
            raise ValueError(f"Could not parse Gemini JSON: {e}\nRaw (first 500): {text[:500]}")

    raise ValueError(f"No JSON object found in Gemini response. Raw (first 200): {text[:200]}")


def _parse_gemini_response(text: str) -> dict:
    """Parse and validate Gemini JSON response."""
    data = _parse_json_response(text)

    # Validate required structure
    required_score_keys = {"task_response", "coherence", "lexical", "grammar", "overall"}
    required_feedback_keys = {"task_response", "coherence", "lexical", "grammar", "improvements"}

    if "scores" not in data or "feedback" not in data:
        raise ValueError("Missing 'scores' or 'feedback' in Gemini response.")

    missing_scores = required_score_keys - set(data["scores"].keys())
    if missing_scores:
        raise ValueError(f"Missing score keys: {missing_scores}")

    missing_feedback = required_feedback_keys - set(data["feedback"].keys())
    if missing_feedback:
        raise ValueError(f"Missing feedback keys: {missing_feedback}")

    # Validate and round score ranges (only criteria; overall is recalculated in sanitization)
    CRITERIA = ["task_response", "coherence", "lexical", "grammar"]
    for key in CRITERIA:
        try:
            score = float(data["scores"].get(key, 0.0) or 0.0)
        except (ValueError, TypeError):
            score = 0.0
        # Only range-check non-zero scores (0.0 is a safe default fallback)
        if score > 0.0 and not (1.0 <= score <= 9.0):
            raise ValueError(f"Score '{key}' out of range: {score}")
        data["scores"][key] = round(score * 2) / 2

    return data


def evaluate_task1(
    image_url: str,
    essay_text: str,
    task_question: str | None = None,
    image_data: Optional[bytes] = None,
) -> dict:
    """
    Evaluates an IELTS Task 1 response using Gemini 2.5 Flash.

    Args:
        image_url: URL of the chart image (for cache key generation).
        essay_text: The candidate's written response.
        image_data: Raw image bytes to send to Gemini.

    Returns:
        dict with keys: scores, feedback, model_used, cache_hit
    """
    cache_key = _cache_key(image_url, essay_text, task_question)

    # Check cache first
    cached = cache.get(cache_key)
    if cached:
        logger.info("Cache hit for Task 1 evaluation: %s", cache_key[:16])
        cached["cache_hit"] = True
        return cached

    pool = get_flash_pool()

    try:
        model, api_key = pool.get_client()
    except AllKeysExhaustedError as e:
        raise RuntimeError(str(e))

    prompt_text = TASK1_PROMPT.format(
        essay=essay_text,
        task_question=task_question or "Not provided (refer to image)"
    )

    # Build multimodal content
    content_parts = []
    if image_data:
        # Detect MIME type (default to JPEG)
        mime_type = "image/jpeg"
        if image_data[:4] == b"\x89PNG":
            mime_type = "image/png"
        elif image_data[:4] == b"GIF8":
            mime_type = "image/gif"
        elif image_data[:2] == b"\xff\xd8":
            mime_type = "image/jpeg"

        content_parts.append({"mime_type": mime_type, "data": image_data})

    content_parts.append(prompt_text)

    try:
        response = model.generate_content(
            content_parts,
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=3000,
            ),
        )
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower():
            pool.mark_exhausted(api_key)
            # Retry with a different key
            return evaluate_task1(image_url, essay_text, image_data)
        raise

    result_text = response.text.strip()

    try:
        parsed = _parse_gemini_response(result_text)
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error("Failed to parse Gemini Task 1 response: %s\nRaw: %s", e, result_text[:500])
        raise ValueError(f"AI returned an invalid response. Please try again. ({e})")

    result = {
        "scores": parsed["scores"],
        "feedback": parsed["feedback"],
        "model_used": "gemini-3-flash-preview",
        "cache_hit": False,
    }

    # ── Final Sanitization ──────────────────────────────────────────────────
    # Ensure all scores are strictly floats and recalculate overall band
    # as the IELTS standard: average of 4 criteria rounded to nearest 0.5
    try:
        if "scores" in result:
            s = result["scores"]
            CRITERIA = ["task_response", "coherence", "lexical", "grammar"]
            for k in CRITERIA + ["overall"]:
                try:
                    s[k] = float(s.get(k, 0.0) or 0.0)
                except (ValueError, TypeError):
                    s[k] = 0.0

            # Always recalculate overall as the mean of 4 criteria, rounded to nearest 0.5
            criteria_vals = [s[k] for k in CRITERIA if s.get(k, 0.0) > 0]
            if criteria_vals:
                raw_avg = sum(criteria_vals) / len(criteria_vals)
                # Round to nearest 0.5 (IELTS standard)
                s["overall"] = round(raw_avg * 2) / 2
            result["scores"] = s
    except Exception as e:
        logger.error("Final score sanitization failed in Task 1: %s", e)

    # Cache the result for 2 hours
    cache.set(cache_key, result, timeout=CACHE_TTL)
    logger.info(
        "Task 1 evaluation complete. Overall: %s", result.get("scores", {}).get("overall")
    )

    return result
