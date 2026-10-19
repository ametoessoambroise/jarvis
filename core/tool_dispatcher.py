"""Tool dispatcher — validation, import tardif, exécution bornée, ToolResult.

Ce module est le seul point d'entrée pour exécuter un outil via le registre.
Il ne sait rien de JarvisLive : les handlers internes (__internal__) sont
interceptés en amont par JarvisLive avant d'appeler dispatch().

Référence : BACKEND_SCHEMA.md §2.3-2.5 — ToolResult, ErrorCode, ResultStatus [V1]
"""

from __future__ import annotations

import importlib
import time
import traceback
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from core.tool_registry import ToolSpec


# ─────────────────────────────────────────────────────────────────────────────
# Types — BACKEND_SCHEMA.md §2.4-2.5
# ─────────────────────────────────────────────────────────────────────────────

class ErrorCode(StrEnum):
    CONFIG_MISSING          = "config_missing"
    AUTH_FAILED             = "auth_failed"
    PROVIDER_UNAVAILABLE    = "provider_unavailable"
    NETWORK_DOWN            = "network_down"
    CAPABILITY_MISSING      = "capability_missing"
    RATE_LIMITED            = "rate_limited"
    VALIDATION_FAILED       = "validation_failed"
    PERMISSION_DENIED       = "permission_denied"
    CONFIRMATION_DECLINED   = "confirmation_declined"
    TIMEOUT                 = "timeout"
    CANCELLED               = "cancelled"
    PLATFORM_UNSUPPORTED    = "platform_unsupported"
    DEPENDENCY_MISSING      = "dependency_missing"
    ACTION_FAILED           = "action_failed"
    VERIFICATION_FAILED     = "verification_failed"
    BUDGET_EXCEEDED         = "budget_exceeded"
    INTERNAL                = "internal"


class ResultStatus(StrEnum):
    OK          = "ok"
    UNVERIFIED  = "unverified"
    ERROR       = "error"
    DECLINED    = "declined"
    CANCELLED   = "cancelled"


@dataclass(frozen=True)
class ToolResult:
    """Résultat d'une exécution d'outil (BACKEND_SCHEMA.md §2.4)."""

    status: ResultStatus
    """Statut de l'exécution."""

    message: str
    """Message court, lisible, sans secret — ≤ ~4 000 caractères."""

    error: ErrorCode | None = None
    """Code d'erreur si status != OK / UNVERIFIED."""

    duration_ms: int = 0
    """Durée d'exécution mesurée."""

    data: dict[str, Any] | None = None
    """Données structurées optionnelles (non envoyées au modèle)."""

    def to_model_response(self) -> dict:
        """Format de réponse V1 envoyé au modèle Gemini.

        Rétro-compatible : le champ "result" est le seul obligatoire.
        Les champs additionnels status/verified sont ignorables par le modèle.
        """
        return {
            "result": self.message,
            "status": str(self.status),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Résolution tardive du handler
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_handler(handler_path: str):
    """Importe et retourne la callable désignée par un chemin dotté.

    Format : "module.submodule:function_name"
    Exemple : "actions.open_app:open_app"
    """
    if ":" not in handler_path:
        raise ImportError(f"Invalid handler path (missing ':'): {handler_path!r}")
    module_path, func_name = handler_path.rsplit(":", 1)
    module = importlib.import_module(module_path)
    fn = getattr(module, func_name, None)
    if fn is None:
        raise ImportError(
            f"Function {func_name!r} not found in module {module_path!r}"
        )
    return fn


# ─────────────────────────────────────────────────────────────────────────────
# Validation des paramètres
# ─────────────────────────────────────────────────────────────────────────────

def _validate_params(spec: ToolSpec, params: dict) -> list[str]:
    """Retourne la liste des paramètres required manquants."""
    required = spec.parameters.get("required", [])
    missing = [r for r in required if r not in params or params[r] is None]
    return missing


# ─────────────────────────────────────────────────────────────────────────────
# Appel de l'action — normalisation de la signature
# ─────────────────────────────────────────────────────────────────────────────

def _call_action(fn, params: dict, context: dict | None) -> str | None:
    """Appelle fn avec la convention de signature JARVIS.

    La plupart des actions acceptent :
        (parameters, response=None, player=None, session_memory=None)

    Certaines acceptent aussi `speak` (code_helper, dev_agent, etc.) ou
    `jarvis` (manage_autonomy) — ces cas sont gérés par les handlers internes
    de JarvisLive, donc dispatch() ne les voit jamais.

    On passe player=None par défaut (le dispatcher est agnostique de l'UI).
    """
    import inspect
    sig = inspect.signature(fn)
    kwargs: dict = {}

    if "parameters" in sig.parameters:
        kwargs["parameters"] = params
    if "response" in sig.parameters:
        kwargs["response"] = None
    if "player" in sig.parameters:
        kwargs["player"] = context.get("player") if context else None
    if "session_memory" in sig.parameters:
        kwargs["session_memory"] = None
    if "speak" in sig.parameters:
        kwargs["speak"] = context.get("speak") if context else None

    return fn(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# dispatch() — point d'entrée principal
# ─────────────────────────────────────────────────────────────────────────────

def dispatch(
    spec: ToolSpec,
    params: dict,
    context: dict | None = None,
) -> ToolResult:
    """Valide, importe et exécute un outil ; retourne toujours un ToolResult.

    Args:
        spec:    ToolSpec du registre (doit être non-None, non-internal).
        params:  Paramètres bruts du modèle.
        context: Dictionnaire optionnel : {"player": ui, "speak": fn}.

    Returns:
        ToolResult — jamais d'exception levée hors de cette fonction.
    """
    # Garde : les handlers internes ne passent PAS par dispatch()
    if spec.is_internal:
        return ToolResult(
            status=ResultStatus.ERROR,
            message=f"L'outil '{spec.name}' est un handler interne — ne pas appeler dispatch() directement.",
            error=ErrorCode.INTERNAL,
        )

    # ── 1. Validation des paramètres required ────────────────────────────────
    missing = _validate_params(spec, params)
    if missing:
        return ToolResult(
            status=ResultStatus.ERROR,
            message=f"Paramètres requis manquants pour '{spec.name}': {missing}",
            error=ErrorCode.VALIDATION_FAILED,
        )

    # ── 2. Import tardif du handler ──────────────────────────────────────────
    try:
        fn = _resolve_handler(spec.handler)
    except (ImportError, AttributeError) as exc:
        return ToolResult(
            status=ResultStatus.ERROR,
            message=f"Impossible de charger le handler de '{spec.name}'.",
            error=ErrorCode.DEPENDENCY_MISSING,
            data={"detail": str(exc)},
        )

    # ── 3. Exécution avec timeout via threading ──────────────────────────────
    import threading

    result_container: dict = {}
    error_container: dict = {}

    def _run():
        try:
            result_container["value"] = _call_action(fn, params, context)
        except Exception as exc:  # noqa: BLE001
            error_container["exc"] = exc
            error_container["tb"]  = traceback.format_exc()

    t0 = time.monotonic()
    thread = threading.Thread(target=_run, daemon=True, name=f"dispatch-{spec.name}")
    thread.start()
    thread.join(timeout=spec.timeout_s)
    duration_ms = int((time.monotonic() - t0) * 1000)

    # ── 4. Timeout ───────────────────────────────────────────────────────────
    if thread.is_alive():
        return ToolResult(
            status=ResultStatus.ERROR,
            message=f"L'outil '{spec.name}' a dépassé le délai de {spec.timeout_s:.0f}s.",
            error=ErrorCode.TIMEOUT,
            duration_ms=duration_ms,
        )

    # ── 5. Exception dans l'action ───────────────────────────────────────────
    if "exc" in error_container:
        exc = error_container["exc"]
        # Message sûr : pas de stacktrace vers le modèle
        print(f"[Dispatcher] ❌ {spec.name} raised: {error_container['tb']}")
        return ToolResult(
            status=ResultStatus.ERROR,
            message=f"L'outil '{spec.name}' a échoué : {_safe_error_message(exc)}",
            error=ErrorCode.ACTION_FAILED,
            duration_ms=duration_ms,
        )

    # ── 6. Résultat vide → UNVERIFIED ────────────────────────────────────────
    raw = result_container.get("value")
    if not raw:
        return ToolResult(
            status=ResultStatus.UNVERIFIED,
            message="terminé, non vérifié",
            duration_ms=duration_ms,
        )

    # ── 7. Succès ─────────────────────────────────────────────────────────────
    return ToolResult(
        status=ResultStatus.OK,
        message=str(raw),
        duration_ms=duration_ms,
    )


def _safe_error_message(exc: Exception) -> str:
    """Retourne un message d'erreur sans information sensible ni chemin interne."""
    msg = str(exc)
    # Tronquer les messages très longs (stacktraces accidentelles)
    if len(msg) > 200:
        msg = msg[:200] + "…"
    return msg
