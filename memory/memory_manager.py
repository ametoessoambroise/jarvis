import json
from datetime import datetime
from threading import Lock
from pathlib import Path
import sys

from config import settings

MEMORY_PATH = settings.paths.memory_dir / "long_term.json"
MEMORY_DIR = settings.paths.memory_dir
_lock = Lock()
MAX_VALUE_LENGTH = 380
MEMORY_MAX_CHARS = 8000

MEMORY_DOC_FILES = {
    "identity": "USER_IDENTITY.md",
    "preferences": "USER_PREFERENCES.md",
    "projects": "USER_PROJECTS.md",
    "routines": "USER_ROUTINES.md",
    "context": "USER_CONTEXT.md",
    "skills": "USER_SKILLS.md",
    "relationships": "USER_RELATIONS.md",
}


def _empty_memory() -> dict:
    return {
        "identity": {},
        "preferences": {},
        "projects": {},
        "routines": {},
        "context": {},
        "skills": {},
        "relationships": {},
        "wishes": {},
        "notes": {},
    }


def load_memory() -> dict:
    if not MEMORY_PATH.exists():
        return _empty_memory()
    with _lock:
        try:
            data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _empty_memory()
                for key in base:
                    if key not in data:
                        data[key] = {}
                return data
            return _empty_memory()
        except Exception as e:
            print(f"[Memory] ⚠️ Load error: {e}")
            return _empty_memory()


def _all_entries(memory: dict) -> list[tuple]:
    entries = []
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            if isinstance(entry, dict) and "value" in entry:
                entries.append((cat, key, entry))
    return entries


def _trim_to_limit(memory: dict) -> dict:
    if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
        return memory
    entries = _all_entries(memory)
    entries.sort(key=lambda t: t[2].get("updated", "0000-00-00"))
    trimmed: list[str] = []
    for cat, key, _ in entries:
        if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
            break
        del memory[cat][key]
        trimmed.append(f"{cat}/{key}")
    if trimmed:
        print(
            f"[Memory] ⚠️ Trimmed {len(trimmed)} old entries to stay under limit: {trimmed}"
        )
    return memory


def save_memory(memory: dict) -> None:
    if not isinstance(memory, dict):
        return
    memory = _trim_to_limit(memory)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        # Write to a temp file first, then atomically rename to avoid corruption
        tmp_path = MEMORY_PATH.with_suffix(".json.tmp")
        bak_path = MEMORY_PATH.with_suffix(".json.bak")
        try:
            tmp_path.write_text(
                json.dumps(memory, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            # Keep one backup of the previous good save
            if MEMORY_PATH.exists():
                import shutil as _shutil

                _shutil.copy2(MEMORY_PATH, bak_path)
            tmp_path.replace(MEMORY_PATH)
        except Exception as exc:
            print(f"[Memory] ❌ Save failed: {exc}")
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return
        save_memory_docs(memory)


def _entry_text(entry: dict) -> str:
    if isinstance(entry, dict):
        return str(entry.get("value", "")).strip()
    return str(entry).strip()


def _write_markdown_file(file_name: str, content: str) -> None:
    target_path = MEMORY_DIR / file_name
    target_path.write_text(content, encoding="utf-8")


def _format_dict_bullets(entries: dict) -> str:
    lines = []
    for key, entry in entries.items():
        value = _entry_text(entry)
        if value:
            lines.append(f"- {key.replace('_', ' ').title()}: {value}")
    return "\n".join(lines)


def _format_identity_md(identity: dict) -> str:
    header = "# USER IDENTITY\n\n"
    lines = [header, "## Identité de base\n"]
    basic_fields = [
        "name",
        "location",
        "city",
        "country",
        "timezone",
        "language",
        "secondary_language",
    ]
    for field in basic_fields:
        entry = identity.get(field)
        if entry:
            lines.append(f"- {field.replace('_', ' ').title()}: {_entry_text(entry)}\n")

    other_fields = {k: v for k, v in identity.items() if k not in basic_fields}
    if other_fields:
        lines.append("\n## Personnalité\n")
        lines.append(_format_dict_bullets(other_fields))
        lines.append("\n")

    lines.append(
        "---\n*Dernière mise à jour : {}*\n".format(datetime.now().strftime("%Y-%m-%d"))
    )
    return "\n".join(lines)


def _format_preferences_md(preferences: dict) -> str:
    header = "# USER PREFERENCES\n\n"
    body = _format_dict_bullets(preferences)
    if not body:
        body = "- [No saved preferences yet]"
    return f"{header}{body}\n\n---\n*Dernière mise à jour : {datetime.now().strftime('%Y-%m-%d')}*\n"


def _format_projects_md(projects: dict) -> str:
    header = "# USER PROJECTS\n\n"
    lines = [header, "## Projets actifs\n"]
    if not projects:
        lines.append("- [No active projects recorded yet]\n")
    else:
        for key, entry in projects.items():
            lines.append(f"### {key.replace('_', ' ').title()}\n")
            value = _entry_text(entry)
            for line in value.splitlines():
                lines.append(f"- {line}\n")
            lines.append("\n")
    lines.append(
        "---\n*Dernière mise à jour : {}*\n".format(datetime.now().strftime("%Y-%m-%d"))
    )
    return "\n".join(lines)


def _format_generic_section(title: str, data: dict, fallback: str) -> str:
    header = f"# {title}\n\n"
    if not data:
        return f"{header}{fallback}\n\n---\n*Dernière mise à jour : {datetime.now().strftime('%Y-%m-%d')}*\n"
    body = _format_dict_bullets(data)
    return f"{header}{body}\n\n---\n*Dernière mise à jour : {datetime.now().strftime('%Y-%m-%d')}*\n"


def save_memory_docs(memory: dict) -> None:
    if not isinstance(memory, dict):
        return
    for category, file_name in MEMORY_DOC_FILES.items():
        data = memory.get(category, {}) or {}
        if category == "identity":
            content = _format_identity_md(data)
        elif category == "projects":
            content = _format_projects_md(data)
        elif category == "preferences":
            content = _format_preferences_md(data)
        elif category == "routines":
            content = _format_generic_section(
                "USER ROUTINES", data, "- [No routines saved yet]"
            )
        elif category == "context":
            content = _format_generic_section(
                "USER CONTEXT — Ce qui est chaud maintenant",
                data,
                "- [No current context saved yet]",
            )
        elif category == "skills":
            content = _format_generic_section(
                "USER SKILLS", data, "- [No skill entries saved yet]"
            )
        elif category == "relationships":
            content = _format_generic_section(
                "USER RELATIONS", data, "- [No relationship entries saved yet]"
            )
        else:
            content = _format_generic_section(
                file_name.replace("USER_", "USER ").replace(".md", ""),
                data,
                "- [No entries saved yet]",
            )
        _write_markdown_file(file_name, content)


def _truncate_value(val: str) -> str:
    if isinstance(val, str) and len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH].rstrip() + "…"
    return val


def _recursive_update(target: dict, updates: dict) -> bool:
    changed = False
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value):
                changed = True
        else:
            new_val = _truncate_value(
                str(value["value"] if isinstance(value, dict) else value)
            )
            entry = {"value": new_val, "updated": datetime.now().strftime("%Y-%m-%d")}
            existing = target.get(key, {})
            if not isinstance(existing, dict) or existing.get("value") != new_val:
                target[key] = entry
                changed = True
    return changed


def update_memory(memory_update: dict) -> dict:
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory()
    memory = load_memory()
    if _recursive_update(memory, memory_update):
        save_memory(memory)
        print(f"[Memory] 💾 Saved: {list(memory_update.keys())}")
    return memory


def format_memory_for_prompt(memory: dict | None) -> str:
    if not memory:
        return ""

    lines = []

    identity = memory.get("identity", {})
    id_fields = [
        "name",
        "age",
        "birthday",
        "city",
        "job",
        "language",
        "school",
        "nationality",
    ]
    for field in id_fields:
        entry = identity.get(field)
        if entry:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"{field.title()}: {val}")
    for key, entry in identity.items():
        if key in id_fields:
            continue
        val = entry.get("value") if isinstance(entry, dict) else entry
        if val:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")

    prefs = memory.get("preferences", {})
    if prefs:
        lines.append("")
        lines.append("Preferences:")
        for key, entry in list(prefs.items())[:15]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    projects = memory.get("projects", {})
    if projects:
        lines.append("")
        lines.append("Active Projects / Goals:")
        for key, entry in list(projects.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    rels = memory.get("relationships", {})
    if rels:
        lines.append("")
        lines.append("People in their life:")
        for key, entry in list(rels.items())[:10]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    routines = memory.get("routines", {})
    if routines:
        lines.append("")
        lines.append("Daily routines and cadence:")
        for key, entry in list(routines.items())[:10]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    context = memory.get("context", {})
    if context:
        lines.append("")
        lines.append("Current context / top of mind:")
        for key, entry in list(context.items())[:10]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    skills = memory.get("skills", {})
    if skills:
        lines.append("")
        lines.append("Skills and tools:")
        for key, entry in list(skills.items())[:10]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    wishes = memory.get("wishes", {})
    if wishes:
        lines.append("")
        lines.append("Wishes / Plans / Wants:")
        for key, entry in list(wishes.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    notes = memory.get("notes", {})
    if notes:
        lines.append("")
        lines.append("Other notes:")
        for key, entry in list(notes.items())[:8]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key}: {val}")

    if not lines:
        return ""

    header = (
        "[WHAT YOU KNOW ABOUT THIS PERSON — use naturally, never recite like a list]\n"
    )
    result = header + "\n".join(lines)
    if len(result) > 2000:
        result = result[:1997] + "…"

    return result + "\n"


def remember(key: str, value: str, category: str = "notes") -> str:
    valid = {
        "identity",
        "preferences",
        "projects",
        "relationships",
        "wishes",
        "notes",
        "routines",
        "context",
        "skills",
    }
    if category not in valid:
        category = "notes"
    update_memory({category: {key: {"value": value}}})
    return f"Remembered: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    memory = load_memory()
    cat = memory.get(category, {})
    if key in cat:
        del cat[key]
        memory[category] = cat
        save_memory(memory)
        return f"Forgotten: {category}/{key}"
    return f"Not found: {category}/{key}"


forget_memory = forget
