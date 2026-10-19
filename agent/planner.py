import json
import re
import sys
from pathlib import Path

from config import settings

# Centralised API key — never duplicate this logic
from core.utils import _get_api_key  # noqa: E402

BASE_DIR = settings.paths.root

from core.tool_registry import _REGISTRY

_PROMPT_HEADER = """You are the planning module of MARK XXXIX, a personal AI assistant.
Your job: break any user goal into a sequence of steps using ONLY the tools listed below.

ABSOLUTE RULES:
- NEVER use generated_code or write Python scripts. It does not exist.
- NEVER reference previous step results in parameters. Every step is independent.
- Use web_search for ANY information retrieval, research, or current data.
- Use file_controller to save content to disk.
- Max 5 steps. Use the minimum steps needed.

AVAILABLE TOOLS AND THEIR PARAMETERS:
"""

_TOOL_DESCRIPTIONS = {
    "open_app": (
        "open_app\n"
        "  app_name: string (required)"
    ),
    "web_search": (
        "web_search\n"
        "  query: string (required) — write a clear, focused search query\n"
        '  mode: "search" or "compare" (optional, default: search)\n'
        "  items: list of strings (optional, for compare mode)\n"
        "  aspect: string (optional, for compare mode)"
    ),
    "game_updater": (
        "game_updater\n"
        '  action: "update" | "install" | "list" | "download_status" | "schedule" (required)\n'
        '  platform: "steam" | "epic" | "both" (optional, default: both)\n'
        "  game_name: string (optional)\n"
        "  app_id: string (optional)\n"
        "  shutdown_when_done: boolean (optional)"
    ),
    "browser_control": (
        "browser_control\n"
        '  action: "go_to" | "search" | "click" | "type" | "scroll" | "get_text" | "press" | "close" (required)\n'
        "  url: string (for go_to)\n"
        "  query: string (for search)\n"
        "  text: string (for click/type)\n"
        '  direction: "up" | "down" (for scroll)'
    ),
    "file_controller": (
        "file_controller\n"
        '  action: "write" | "create_file" | "read" | "list" | "delete" | "move" | "copy" | "find" | "disk_usage" (required)\n'
        '  path: string — use "desktop" for Desktop folder\n'
        "  name: string — filename\n"
        "  content: string — file content (for write/create_file)"
    ),
    "computer_settings": (
        "computer_settings\n"
        "  action: string (required)\n"
        "  description: string — natural language description\n"
        "  value: string (optional)"
    ),
    "computer_control": (
        "computer_control\n"
        '  action: "type" | "click" | "hotkey" | "press" | "scroll" | "screenshot" | "screen_find" | "screen_click" (required)\n'
        "  text: string (for type)\n"
        "  x, y: int (for click)\n"
        '  keys: string (for hotkey, e.g. "ctrl+c")\n'
        "  key: string (for press)\n"
        '  direction: "up" | "down" (for scroll)\n'
        "  description: string (for screen_find/screen_click)"
    ),
    "screen_process": (
        "screen_process\n"
        "  text: string (required) — what to analyze or ask about the screen\n"
        '  angle: "screen" | "camera" (optional)'
    ),
    "send_message": (
        "send_message\n"
        "  receiver: string (required)\n"
        "  message_text: string (required)\n"
        "  platform: string (required)"
    ),
    "reminder": (
        "reminder\n"
        "  date: string YYYY-MM-DD (required)\n"
        "  time: string HH:MM (required)\n"
        "  message: string (required)"
    ),
    "desktop_control": (
        "desktop_control\n"
        '  action: "wallpaper" | "organize" | "clean" | "list" | "task" (required)\n'
        "  path: string (optional)\n"
        "  task: string (optional)"
    ),
    "youtube_video": (
        "youtube_video\n"
        '  action: "play" | "summarize" | "trending" (required)\n'
        "  query: string (for play)"
    ),
    "weather_report": (
        "weather_report\n"
        "  city: string (required)"
    ),
    "flight_finder": (
        "flight_finder\n"
        "  origin: string (required)\n"
        "  destination: string (required)\n"
        "  date: string (required)"
    ),
    "code_helper": (
        "code_helper\n"
        '  action: "write" | "edit" | "run" | "explain" (required)\n'
        "  description: string (required)\n"
        "  language: string (optional)\n"
        "  output_path: string (optional)\n"
        "  file_path: string (optional)"
    ),
    "dev_agent": (
        "dev_agent\n"
        "  description: string (required)\n"
        "  language: string (optional)"
    ),
}

_PROMPT_EXAMPLES = """EXAMPLES:

Goal: "research mechanical engineering and save it to a notepad file"
Steps:

web_search | query: "mechanical engineering overview definition history"
web_search | query: "mechanical engineering applications and future trends"
file_controller | action: write, path: desktop, name: mechanical_engineering.txt, content: "MECHANICAL ENGINEERING RESEARCH\\n\\nThis file will be filled with web research results."

Goal: "What is the price of Bitcoin"
Steps:

web_search | query: "Bitcoin price today USD"

Goal: "List the files on the desktop and find the largest 5 files"
Steps:

file_controller | action: list, path: desktop
file_controller | action: largest, path: desktop, count: 5

Goal: "Install PUBG from Steam"
Steps:

game_updater | action: install, platform: steam, game_name: "PUBG"

Goal: "Update all my Steam games"
Steps:

game_updater | action: update, platform: steam

Goal: "Send John a message on WhatsApp saying there is a meeting tomorrow"
Steps:

send_message | receiver: John, message_text: "There is a meeting tomorrow", platform: WhatsApp

Goal: "Open the clock and set a reminder for 30 minutes later"
Steps:

reminder | date: [today], time: [now+30min], message: "Reminder"

OUTPUT — return ONLY valid JSON, no markdown, no explanation, no code blocks:
{
  "goal": "...",
  "steps": [
    {
      "step": 1,
      "tool": "tool_name",
      "description": "what this step does",
      "parameters": {},
      "critical": true
    }
  ]
}
"""


def _build_planner_prompt() -> str:
    """Construit le prompt de planification à partir des outils du registre ayant planner=True."""
    docs = []
    for spec in _REGISTRY.planner_tools():
        if spec.name in _TOOL_DESCRIPTIONS:
            docs.append(_TOOL_DESCRIPTIONS[spec.name])
    return _PROMPT_HEADER + "\n" + "\n\n".join(docs) + "\n\n" + _PROMPT_EXAMPLES


PLANNER_PROMPT = _build_planner_prompt()


def create_plan(goal: str, context: str = "") -> dict:
    import google.generativeai as genai

    genai.configure(api_key=_get_api_key())
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite", system_instruction=PLANNER_PROMPT
    )

    MAX_GOAL_LEN = 500
    sanitized_goal = goal[:MAX_GOAL_LEN].replace("\n", " ").strip()
    user_input = f"Goal: {sanitized_goal}"
    if context:
        user_input += f"\n\nContext: {context[:300]}"

    try:
        response = model.generate_content(user_input)
        text = response.text.strip()
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

        plan = json.loads(text)

        if "steps" not in plan or not isinstance(plan["steps"], list):
            raise ValueError("Invalid plan structure")

        for step in plan["steps"]:
            if step.get("tool") in ("generated_code",):
                print(
                    f"[Planner] ⚠️ generated_code detected in step {step.get('step')} — replacing with web_search"
                )
                desc = step.get("description", goal)
                step["tool"] = "web_search"
                step["parameters"] = {"query": desc[:200]}

        print(f"[Planner] ✅ Plan: {len(plan['steps'])} steps")
        for s in plan["steps"]:
            print(f"  Step {s['step']}: [{s['tool']}] {s['description']}")

        return plan

    except json.JSONDecodeError as e:
        print(f"[Planner] ⚠️ JSON parse failed: {e}")
        return _fallback_plan(goal)
    except Exception as e:
        print(f"[Planner] ⚠️ Planning failed: {e}")
        return _fallback_plan(goal)


def _fallback_plan(goal: str) -> dict:
    print("[Planner] 🔄 Fallback plan")
    return {
        "goal": goal,
        "steps": [
            {
                "step": 1,
                "tool": "web_search",
                "description": f"Search for: {goal}",
                "parameters": {"query": goal},
                "critical": True,
            }
        ],
    }


def replan(goal: str, completed_steps: list, failed_step: dict, error: str) -> dict:
    import google.generativeai as genai

    genai.configure(api_key=_get_api_key())
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash", system_instruction=PLANNER_PROMPT
    )

    completed_summary = "\n".join(
        f"  - Step {s['step']} ({s['tool']}): DONE" for s in completed_steps
    )

    prompt = f"""Goal: {goal}

Already completed:
{completed_summary if completed_summary else '  (none)'}

Failed step: [{failed_step.get('tool')}] {failed_step.get('description')}
Error: {error}

Create a REVISED plan for the remaining work only. Do not repeat completed steps."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
        plan = json.loads(text)

        for step in plan.get("steps", []):
            if step.get("tool") == "generated_code":
                step["tool"] = "web_search"
                step["parameters"] = {"query": step.get("description", goal)[:200]}

        print(f"[Planner] 🔄 Revised plan: {len(plan['steps'])} steps")
        return plan
    except Exception as e:
        print(f"[Planner] ⚠️ Replan failed: {e}")
        return _fallback_plan(goal)
