"""
Task 2 evaluator — Gemini-powered pipeline:
  1. Calls Gemini 2.0 Flash Lite for full evaluation (scores + feedback).
  2. Caches results by SHA-256 of essay + question for 2 hours.
"""

import hashlib
import json
import re
import logging

from django.conf import settings
from django.core.cache import cache

import google.generativeai as genai
from .gemini_pool import get_lite_pool, AllKeysExhaustedError

logger = logging.getLogger(__name__)

CACHE_TTL = 7200  # 2 hours

# ─────────────────────────────────────────────
# Prompt
# ─────────────────────────────────────────────
FULL_EVAL_PROMPT = """You are a certified IELTS Writing examiner with 10+ years of experience.

Task: Evaluate the following IELTS Writing Task 2 essay.

Question: {task_question}

Essay: {essay}
Word count: {word_count}

Score on each of the 4 IELTS criteria (0-9, in 0.5 increments). Be strict — do not inflate scores.
Provide concise feedback per criterion (2-3 sentences each) and exactly 4 specific actionable improvements.

You MUST output ONLY a raw JSON object — no markdown, no code fences, no explanation. Use EXACTLY these key names:
{{
  "scores": {{
    "task_response": <number 1.0-9.0>,
    "coherence": <number 1.0-9.0>,
    "lexical": <number 1.0-9.0>,
    "grammar": <number 1.0-9.0>,
    "overall": <average of the four scores above, rounded to nearest 0.5>
  }},
  "feedback": {{
    "task_response": "<feedback>",
    "coherence": "<feedback>",
    "lexical": "<feedback>",
    "grammar": "<feedback>",
    "improvements": ["<improvement 1>", "<improvement 2>", "<improvement 3>", "<improvement 4>"]
  }}
}}"""


# ─────────────────────────────────────────────
# JSON parsing helper
# ─────────────────────────────────────────────
def _parse_json_response(text: str) -> dict:
    """
    Robustly parse a JSON response from Gemini.
    Handles: markdown fences (open or unclosed), trailing commas,
    key normalization, and truncated responses.
    """
    text = text.strip()

    # 1. Strip markdown fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        unclosed = re.match(r'^```(?:json)?\s*([\s\S]+)', text)
        if unclosed:
            text = unclosed.group(1).strip()

    # 2. Try direct parse
    try:
        return _normalize_keys(json.loads(text))
    except json.JSONDecodeError:
        pass

    # 3. Strip trailing commas then try again
    cleaned = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return _normalize_keys(json.loads(cleaned))
    except json.JSONDecodeError:
        pass

    # 4. Extract first balanced JSON object
    obj_match = re.search(r'(\{[\s\S]*\})', cleaned)
    if obj_match:
        candidate = obj_match.group(1)
        try:
            return _normalize_keys(json.loads(candidate))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Could not parse JSON from Gemini output: {e}\n"
                f"Raw text (first 500 chars): {text[:500]}"
            )

    raise ValueError(
        f"No JSON object found in Gemini response. Raw (first 200): {text[:200]}"
    )


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
        result = {}
        for k, v in obj.items():
            clean_k = k.lower().replace(" ", "_").replace("-", "_")
            new_key = SCORE_KEY_MAP.get(clean_k, clean_k)
            result[new_key] = remap_keys(v) if isinstance(v, dict) else v
        return result

    remapped = remap_keys(data)

    # Extract scores sub-dict
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

    # Extract feedback sub-dict
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


def _round_band(score: float) -> float:
    """Round a score to the nearest 0.5 IELTS band, clamped to 1.0–9.0."""
    clamped = max(1.0, min(9.0, float(score)))
    return round(clamped * 2) / 2


# ─────────────────────────────────────────────
# Gemini full evaluation
# ─────────────────────────────────────────────
def _evaluate_with_gemini(essay: str, task_question: str | None = None) -> dict:
    """
    Full evaluation using Gemini Flash-Lite for both scores and feedback.
    """
    pool = get_lite_pool()
    model, api_key = pool.get_client()

    word_count = len(essay.split())
    prompt = FULL_EVAL_PROMPT.format(
        essay=essay,
        word_count=word_count,
        task_question=task_question or "General IELTS Task 2 topic"
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=3000,
            ),
        )
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            pool.mark_exhausted(api_key)
            raise
        raise

    data = _parse_json_response(response.text)
    return {
        "scores": data["scores"],
        "feedback": data["feedback"],
        "model_used": "gemini-2.0-flash-lite",
    }


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────
def evaluate_task2(essay_text: str, task_question: str | None = None) -> dict:
    """
    Evaluates an IELTS Task 2 essay using Gemini 2.0 Flash Lite.

    Returns:
        dict with keys: scores, feedback, model_used, cache_hit
    """
    # Cache key based on essay + question content
    essay_hash = hashlib.sha256(essay_text.encode()).hexdigest()
    q_hash = hashlib.sha256(task_question.encode()).hexdigest() if task_question else "no_q"
    cache_key = f"task2_eval:{essay_hash}:{q_hash}"

    cached = cache.get(cache_key)
    if cached:
        logger.info("Cache hit for Task 2 evaluation: %s", essay_hash[:16])
        cached["cache_hit"] = True
        return cached

    result = _evaluate_with_gemini(essay_text, task_question=task_question)
    result["cache_hit"] = False

    # ── Final Sanitization ──────────────────────────────────────────────────
    # Ensure all scores are floats and recalculate overall as IELTS standard:
    # average of 4 criteria, rounded to nearest 0.5
    try:
        if "scores" in result:
            s = result["scores"]
            CRITERIA = ["task_response", "coherence", "lexical", "grammar"]
            for k in CRITERIA + ["overall"]:
                try:
                    s[k] = float(s.get(k, 0.0) or 0.0)
                except (ValueError, TypeError):
                    s[k] = 0.0

            criteria_vals = [s[k] for k in CRITERIA if s.get(k, 0.0) > 0]
            if criteria_vals:
                raw_avg = sum(criteria_vals) / len(criteria_vals)
                s["overall"] = _round_band(raw_avg)
            result["scores"] = s
    except Exception as e:
        logger.error("Final score sanitization failed: %s", e)

    logger.info(
        "Task 2 evaluation complete. Overall: %s, Model: %s",
        result.get("scores", {}).get("overall"),
        result["model_used"],
    )

    cache.set(cache_key, result, timeout=CACHE_TTL)
    return result
