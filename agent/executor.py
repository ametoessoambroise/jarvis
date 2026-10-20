import time
import threading
from typing import Callable

from config import settings
from agent.planner import create_plan, replan
from agent.error_handler import analyze_error, ErrorDecision
from agent.execution_types import (
    ExecutionResult,
    ExecutionStatus,
    StepResult,
    StepStatus,
)

# Centralised API key — never duplicate this logic
from core.utils import _get_api_key  # noqa: E402

BASE_DIR = settings.paths.root


def _inject_context(
    params: dict, tool: str, step_results: dict, goal: str = ""
) -> dict:
    if not step_results:
        return params

    params = dict(params)

    if tool == "file_controller" and params.get("action") in ("write", "create_file"):
        content = params.get("content", "")
        if not content or len(content) < 50:
            all_results = [
                v
                for v in step_results.values()
                if v and len(str(v)) > 100 and v not in ("Done.", "Completed.")
            ]
            if all_results:
                combined = "\n\n---\n\n".join(str(r) for r in all_results)
                translated = _translate_to_goal_language(combined, goal)
                params["content"] = translated
                print("[Executor] 💉 Injected + translated content")

    return params


def _detect_language(text: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=_get_api_key())
    model = genai.GenerativeModel("gemini-2.5-flash-lite")
    try:
        response = model.generate_content(
            f"What language is this text written in? "
            f"Reply with ONLY the language name in English (e.g. Turkish, English, French).\n\n"
            f"Text: {text[:200]}"
        )
        return response.text.strip()
    except Exception:
        return "English"


def _translate_to_goal_language(content: str, goal: str) -> str:
    if not goal:
        return content
    try:
        import google.generativeai as genai

        genai.configure(api_key=_get_api_key())
        model = genai.GenerativeModel("gemini-2.5-flash")

        target_lang = _detect_language(goal)
        print(f"[Executor] 🌐 Translating to: {target_lang}")

        prompt = (
            f"You are a professional translator. "
            f"Translate the following text into {target_lang}.\n"
            f"IMPORTANT:\n"
            f"- Translate EVERYTHING, leave nothing in English\n"
            f"- Keep all facts, numbers, and data intact\n"
            f"- Keep the structure and formatting\n"
            f"- Output ONLY the translated text, nothing else\n\n"
            f"Text to translate:\n{content[:4000]}"
        )
        response = model.generate_content(prompt)
        translated = response.text.strip()
        print(f"[Executor] ✅ Translation done ({target_lang})")
        return translated
    except Exception as e:
        print(f"[Executor] ⚠️ Translation failed: {e}")
        return content


def _call_tool(tool: str, parameters: dict, speak: Callable | None) -> str:

    if tool == "screen_process":
        from actions.screen_processor import screen_process

        screen_process(parameters=parameters, player=None)
        return "Screen captured and analyzed."

    from core.tool_registry import _REGISTRY

    spec = _REGISTRY.get(tool)
    if not spec:
        raise ValueError(
            f"Unknown tool '{tool}'. No automatic fallback is allowed — "
            "add this tool to the registry explicitly."
        )

    res = _REGISTRY.call(tool, parameters, context={"player": None, "speak": speak})
    return res.message


class AgentExecutor:
    """Executes a multi-step plan and returns a typed ExecutionResult.

    Status rules (BACKEND_SCHEMA.md §3.3):
      SUCCEEDED : every critical step is OK or UNVERIFIED; no FAILED step.
      PARTIAL   : at least one non-critical step is SKIPPED or FAILED.
      ABORTED   : execution stopped via an ABORT decision.
      FAILED    : critical step failed after all replans exhausted.
      CANCELLED : cancel_flag was set before completion.
    """

    MAX_REPLAN_ATTEMPTS = 2

    def execute(
        self,
        goal: str,
        speak: Callable | None = None,
        cancel_flag: threading.Event | None = None,
    ) -> ExecutionResult:
        print(f"\n[Executor] 🎯 Goal: {goal}")

        replan_count = 0
        step_results: dict[int, str] = {}    # step_num → raw tool output
        all_step_results: list[StepResult] = []
        plan = create_plan(goal)

        while True:
            steps = plan.get("steps", [])

            if not steps:
                msg = "I couldn't create a valid plan for this task, sir."
                if speak:
                    speak(msg)
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    steps=tuple(all_step_results),
                    summary=msg,
                    error="no_plan",
                    replans=replan_count,
                )

            any_failed = False
            failed_step = None
            failed_error = ""

            for step in steps:
                if cancel_flag and cancel_flag.is_set():
                    msg = "Task cancelled, sir."
                    if speak:
                        speak(msg)
                    return ExecutionResult(
                        status=ExecutionStatus.CANCELLED,
                        steps=tuple(all_step_results),
                        summary=msg,
                        replans=replan_count,
                    )

                step_num = step.get("step", len(all_step_results) + 1)
                tool     = step.get("tool", "generated_code")
                desc     = step.get("description", "")
                params   = dict(step.get("parameters", {}))
                critical = step.get("critical", False)

                params = _inject_context(params, tool, step_results, goal=goal)

                print(f"\n[Executor] ▶️ Step {step_num}: [{tool}] {desc}")

                attempt   = 1
                step_ok   = False
                step_status  = StepStatus.FAILED
                step_message = ""
                step_error   = None

                while attempt <= 3:
                    if cancel_flag and cancel_flag.is_set():
                        break
                    try:
                        raw_result = _call_tool(tool, params, speak)
                        step_results[step_num] = raw_result
                        step_ok      = True
                        step_status  = StepStatus.OK
                        step_message = str(raw_result)[:200]
                        print(f"[Executor] ✅ Step {step_num} done: {step_message[:100]}")
                        break

                    except Exception as e:
                        error_msg = str(e)
                        print(
                            f"[Executor] ❌ Step {step_num} attempt {attempt} failed: {error_msg}"
                        )

                        recovery = analyze_error(
                            step, error_msg, attempt=attempt, max_attempts=3
                        )
                        decision = recovery["decision"]
                        user_msg = recovery.get("user_message", "")

                        if speak and user_msg:
                            speak(user_msg)

                        if decision == ErrorDecision.RETRY:
                            attempt += 1
                            time.sleep(2)
                            continue

                        elif decision == ErrorDecision.SKIP:
                            # SKIP is never treated as success — it's skipped.
                            print(f"[Executor] ⏭️ Skipping step {step_num}")
                            step_status  = StepStatus.SKIPPED
                            step_message = f"Skipped: {error_msg[:100]}"
                            step_ok      = True   # don't break the loop, just move on
                            break

                        elif decision == ErrorDecision.ABORT:
                            reason = recovery.get("reason", "")
                            msg = f"Task aborted, sir. {reason}"
                            if speak:
                                speak(msg)
                            all_step_results.append(StepResult(
                                index=step_num, tool=tool,
                                status=StepStatus.FAILED, attempts=attempt,
                                message=step_message, error=error_msg,
                            ))
                            return ExecutionResult(
                                status=ExecutionStatus.ABORTED,
                                steps=tuple(all_step_results),
                                summary=msg,
                                error=error_msg,
                                replans=replan_count,
                            )

                        else:  # REPLAN
                            failed_step  = step
                            failed_error = error_msg
                            any_failed   = True
                            step_error   = error_msg
                            break

                # Record the step result
                all_step_results.append(StepResult(
                    index=step_num, tool=tool,
                    status=step_status, attempts=attempt,
                    message=step_message, error=step_error,
                ))

                if not step_ok:
                    any_failed   = True
                    failed_step  = failed_step or step
                    failed_error = failed_error or "Step failed"

                if any_failed and critical:
                    # Critical failure — break inner step loop to try replan
                    break

            # ── Inner step loop finished ──────────────────────────────────────

            if cancel_flag and cancel_flag.is_set():
                msg = "Task cancelled, sir."
                if speak:
                    speak(msg)
                return ExecutionResult(
                    status=ExecutionStatus.CANCELLED,
                    steps=tuple(all_step_results),
                    summary=msg,
                    replans=replan_count,
                )

            if not any_failed:
                # Check if any step was skipped → PARTIAL, else SUCCEEDED
                has_skipped = any(
                    s.status == StepStatus.SKIPPED for s in all_step_results
                )
                exec_status = ExecutionStatus.PARTIAL if has_skipped else ExecutionStatus.SUCCEEDED
                return self._build_result(
                    exec_status, goal, all_step_results, replan_count, speak
                )

            # ── Failure: decide to replan or give up ─────────────────────────
            if replan_count >= self.MAX_REPLAN_ATTEMPTS:
                msg = (
                    f"Task failed after {replan_count} replan attempt(s), sir. "
                    f"Last error: {failed_error[:100]}"
                )
                if speak:
                    speak(msg)
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    steps=tuple(all_step_results),
                    summary=msg,
                    error=failed_error[:200],
                    replans=replan_count,
                )

            if speak:
                speak("Adjusting my approach, sir.")

            replan_count += 1
            completed_steps = [
                s._asdict() if hasattr(s, "_asdict") else step
                for s, step in zip(all_step_results, plan.get("steps", []))
                if s.status in (StepStatus.OK, StepStatus.UNVERIFIED)
            ]
            plan = replan(goal, completed_steps, failed_step, failed_error)
            # Reset per-replan tracking (keep accumulated results)
            all_step_results = []
            step_results = {}
            any_failed = False

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _build_result(
        self,
        status: ExecutionStatus,
        goal: str,
        step_results: list[StepResult],
        replan_count: int,
        speak: Callable | None,
    ) -> ExecutionResult:
        """Build an ExecutionResult with an honest summary."""
        summary = _build_summary(goal, step_results)
        if speak:
            speak(summary)

        return ExecutionResult(
            status=status,
            steps=tuple(step_results),
            summary=summary,
            replans=replan_count,
        )


def _build_summary(goal: str, step_results: list[StepResult]) -> str:
    """Build an honest natural summary of what was accomplished."""
    ok_count      = sum(1 for s in step_results if s.status == StepStatus.OK)
    skipped_count = sum(1 for s in step_results if s.status == StepStatus.SKIPPED)
    failed_count  = sum(1 for s in step_results if s.status == StepStatus.FAILED)
    total         = len(step_results)

    # Construct a factual fallback summary first
    parts = [f"Completed {ok_count}/{total} steps for: {goal[:60]}."]
    if skipped_count:
        parts.append(f"{skipped_count} step(s) skipped.")
    if failed_count:
        parts.append(f"{failed_count} step(s) failed.")
    fallback = " ".join(parts)

    try:
        import google.generativeai as genai

        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            client_options={"api_key": _get_api_key()},
        )
        steps_str = "\n".join(
            f"- [{s.status}] {s.tool}: {s.message[:80]}"
            for s in step_results
        )
        prompt = (
            f'User goal: "{goal}"\n'
            f"Step outcomes:\n{steps_str}\n\n"
            "Write a single natural sentence summarising what was accomplished. "
            "Mention any steps that were skipped or failed honestly. "
            "Address the user as 'sir'. Be direct."
        )
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return fallback
