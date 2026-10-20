import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from threading import RLock

from config import settings


def _get_memory_dir() -> Path:
    override = os.environ.get("JARVIS_MEMORY_DIR")
    if override:
        return Path(override).resolve()
    # Support monkeypatched MEMORY_DIR if explicitly modified
    if "MEMORY_DIR" in globals() and globals()["MEMORY_DIR"] is not None:
        return globals()["MEMORY_DIR"]
    return settings.paths.memory_dir


def _get_memory_path() -> Path:
    override = os.environ.get("JARVIS_MEMORY_DIR")
    if override:
        return Path(override).resolve() / "long_term.json"
    if "MEMORY_PATH" in globals() and globals()["MEMORY_PATH"] is not None:
        return globals()["MEMORY_PATH"]
    return _get_memory_dir() / "long_term.json"


MEMORY_DIR: Path = settings.paths.memory_dir
MEMORY_PATH: Path = MEMORY_DIR / "long_term.json"

# R-O13: RLock covers entire read-modify-write cycle and prevents reentrant deadlocks
_lock = RLock()

MAX_VALUE_LENGTH = 380
MEMORY_MAX_CHARS = 8000

VALID_CATEGORIES: frozenset[str] = frozenset({
    "identity",
    "preferences",
    "projects",
    "routines",
    "context",
    "skills",
    "relationships",
    "wishes",
    "notes",
})

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
    """Loads memory from long_term.json.

    R-O13: If long_term.json is corrupt, it is quarantined to
    long_term.json.corrupt-<timestamp> and auto-restored from long_term.json.bak
    if the backup is valid JSON.
    """
    mem_path = _get_memory_path()
    if not mem_path.exists():
        return _empty_memory()

    with _lock:
        try:
            raw_text = mem_path.read_text(encoding="utf-8")
            data = json.loads(raw_text)
            if not isinstance(data, dict):
                raise ValueError("Memory JSON root is not an object/dict")
            base = _empty_memory()
            for key in base:
                if key not in data or not isinstance(data[key], dict):
                    data[key] = {}
            return data
        except Exception as exc:
            # Corrupt file recovery
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            corrupt_path = mem_path.with_name(f"long_term.json.corrupt-{ts}")
            print(f"[Memory] ⚠️ Corrupt memory file detected: {exc}. Quarantining to {corrupt_path.name}")
            try:
                shutil.copy2(mem_path, corrupt_path)
            except Exception as copy_err:
                print(f"[Memory] ⚠️ Failed to copy corrupt file to quarantine: {copy_err}")

            bak_path = mem_path.with_suffix(".json.bak")
            if bak_path.exists():
                try:
                    bak_text = bak_path.read_text(encoding="utf-8")
                    bak_data = json.loads(bak_text)
                    if isinstance(bak_data, dict):
                        print(f"[Memory] 🔄 Restoring memory from backup {bak_path.name}")
                        shutil.copy2(bak_path, mem_path)
                        base = _empty_memory()
                        for key in base:
                            if key not in bak_data or not isinstance(bak_data[key], dict):
                                bak_data[key] = {}
                        return bak_data
                except Exception as bak_err:
                    print(f"[Memory] ⚠️ Backup file is also invalid: {bak_err}")

            print("[Memory] ⚠️ No valid backup available. Initializing empty memory structure.")
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
        if cat in memory and key in memory[cat]:
            del memory[cat][key]
            trimmed.append(f"{cat}/{key}")
    if trimmed:
        print(
            f"[Memory] ⚠️ Trimmed {len(trimmed)} old entries to stay under limit ({MEMORY_MAX_CHARS} chars): {trimmed}"
        )
    return memory


def save_memory(memory: dict) -> None:
    """Saves memory atomically.

    R-O13: Only backs up the existing memory file to .bak if it is valid JSON.
    Corrupted files are never copied to .bak.
    """
    if not isinstance(memory, dict):
        return

    with _lock:
        memory = _trim_to_limit(memory)
        mem_dir = _get_memory_dir()
        mem_path = _get_memory_path()
        mem_dir.mkdir(parents=True, exist_ok=True)

        tmp_path = mem_path.with_suffix(".json.tmp")
        bak_path = mem_path.with_suffix(".json.bak")

        # Keep one backup of the previous GOOD save only
        if mem_path.exists():
            try:
                current_text = mem_path.read_text(encoding="utf-8")
                parsed = json.loads(current_text)
                if isinstance(parsed, dict):
                    shutil.copy2(mem_path, bak_path)
            except Exception as e:
                print(f"[Memory] ⚠️ Skipping .bak copy: existing memory is not valid JSON ({e})")

        try:
            tmp_path.write_text(
                json.dumps(memory, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp_path.replace(mem_path)
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
    target_path = _get_memory_dir() / file_name
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
    """Updates memory atomically covering the full read-modify-write cycle.

    R-O13: Uses RLock across the entire cycle and routes unknown categories
    to 'notes' with an explicit warning.
    """
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory()

    with _lock:
        # Validate categories: unknown categories are migrated to "notes" with a warning
        sanitized_update: dict = {}
        for cat, items in memory_update.items():
            if cat not in VALID_CATEGORIES:
                print(f"[Memory] ⚠️ Unknown memory category '{cat}' — routing to 'notes'")
                if "notes" not in sanitized_update:
                    sanitized_update["notes"] = {}
                if isinstance(items, dict):
                    for subk, subv in items.items():
                        sanitized_update["notes"][f"{cat}_{subk}"] = subv
                else:
                    sanitized_update["notes"][str(cat)] = items
            else:
                sanitized_update[cat] = items

        memory = load_memory()
        if _recursive_update(memory, sanitized_update):
            save_memory(memory)
            print(f"[Memory] 💾 Saved: {list(sanitized_update.keys())}")
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
    with _lock:
        if category not in VALID_CATEGORIES:
            print(f"[Memory] ⚠️ Unknown category '{category}' in remember() — fallback to 'notes'")
            category = "notes"
        update_memory({category: {key: {"value": value}}})
        return f"Remembered: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    with _lock:
        memory = load_memory()
        cat = memory.get(category, {})
        if key in cat:
            del cat[key]
            memory[category] = cat
            save_memory(memory)
            return f"Forgotten: {category}/{key}"
        return f"Not found: {category}/{key}"


forget_memory = forget
