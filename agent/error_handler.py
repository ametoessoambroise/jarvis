import json
import re
from enum import Enum

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore[assignment]

from config import settings

# Centralised API key — never duplicate this logic
from core.utils import _get_api_key  # noqa: E402

BASE_DIR = settings.paths.root


class ErrorDecision(Enum):
    RETRY  = "retry"
    SKIP   = "skip"
    REPLAN = "replan"
    ABORT  = "abort"


ERROR_ANALYST_PROMPT = """You are the error recovery module of MARK XXXIX AI assistant.

A task step has failed. Analyze the error and decide what to do.

DECISIONS:
- retry   : Transient error (network timeout, temporary file lock, race condition).
             The same step can succeed if tried again.
- skip    : This step is not critical and the task can succeed without it.
- replan  : The approach was wrong. A different tool or method should be tried.
- abort   : The task is fundamentally impossible or unsafe to continue.

Also provide:
- A brief explanation of WHY it failed (1 sentence)
- A fix suggestion if decision is replan (what to try instead)
- Max retries: how many times to retry if decision is retry (1 or 2)

Return ONLY valid JSON:
{
  "decision": "retry|skip|replan|abort",
  "reason": "why it failed",
  "fix_suggestion": "what to try instead (for replan)",
  "max_retries": 1,
  "user_message": "Short message to tell the user (max 15 words)"
}
"""


def analyze_error(
    step: dict, error: str, attempt: int = 1, max_attempts: int = 3
) -> dict:
    """Analyses a failed step and returns a recovery decision.

    Args:
        step         : The step dict that failed.
        error        : Error message/traceback.
        attempt      : Current attempt number (1-based).
        max_attempts : Maximum allowed attempts before forcing a replan
                       (default: 3 — R-O12 fix, three real attempts).

    Returns:
        {
            "decision": ErrorDecision,
            "reason": str,
            "fix_suggestion": str,
            "max_retries": int,
            "user_message": str
        }
    """
    # Force replan once we have exhausted all attempts.
    if attempt >= max_attempts:
        print(
            f"[ErrorHandler] ⚠️ Max attempts ({max_attempts}) reached for step "
            f"{step.get('step')} — forcing replan"
        )
        return {
            "decision":       ErrorDecision.REPLAN,
            "reason":         f"Failed {attempt} times: {error[:100]}",
            "fix_suggestion": "Try a completely different approach or tool",
            "max_retries":    0,
            "user_message":   "Trying a different approach, sir.",
        }

    if genai is None:
        return {
            "decision":       ErrorDecision.REPLAN,
            "reason":         "google-generativeai not installed",
            "fix_suggestion": "Try alternative approach",
            "max_retries":    0,
            "user_message":   "Adjusting approach, sir.",
        }

    genai.configure(api_key=_get_api_key())
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite", system_instruction=ERROR_ANALYST_PROMPT
    )

    prompt = f"""Failed step:
Tool: {step.get('tool')}
Description: {step.get('description')}
Parameters: {json.dumps(step.get('parameters', {}), indent=2)}
Critical: {step.get('critical', False)}

Error:
{error[:500]}

Attempt number: {attempt}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        result = json.loads(text)
        decision_str = result.get("decision", "replan").lower()
        decision_map = {
            "retry":  ErrorDecision.RETRY,
            "skip":   ErrorDecision.SKIP,
            "replan": ErrorDecision.REPLAN,
            "abort":  ErrorDecision.ABORT,
        }
        result["decision"] = decision_map.get(decision_str, ErrorDecision.REPLAN)

        # Critical steps must never be skipped — escalate to replan.
        if step.get("critical") and result["decision"] == ErrorDecision.SKIP:
            result["decision"]     = ErrorDecision.REPLAN
            result["user_message"] = (
                "This step is critical — finding alternative approach, sir."
            )

        print(
            f"[ErrorHandler] Decision: {result['decision'].value} — {result.get('reason', '')}"
        )
        return result

    except Exception as e:
        print(f"[ErrorHandler] ⚠️ Analysis failed: {e} — defaulting to replan")
        return {
            "decision":       ErrorDecision.REPLAN,
            "reason":         str(e),
            "fix_suggestion": "Try alternative approach",
            "max_retries":    1,
            "user_message":   "Encountered an issue, adjusting approach, sir.",
        }
