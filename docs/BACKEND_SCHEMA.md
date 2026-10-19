# BACKEND_SCHEMA — Structures et modèles de données de JARVIS

| | |
|---|---|
| **Document** | `BACKEND_SCHEMA.md` (8/9) |
| **Rôle** | **Définition unique** des types utilisés par les contrats de `BACKEND_CONTRACT.md` et des données persistées. Aucun autre document ne redéfinit ces structures. |
| **Base** | `main` @ `2dbb971` |
| **Python** | ≥ 3.11 · `dataclasses` + `enum.StrEnum` · `sqlite3` (stdlib) — ADR-023 |
| **Statuts** | **[ACTUEL]** format existant vérifié · **[V1]** transition · **[CIBLE V1.5]** proposé, inexistant |

> Les exemples ne contiennent **aucun** secret, chemin personnel ou donnée réelle. Les valeurs sont factices.

---

## 1. Principes

1. **Une structure = une définition.** Les contrats y renvoient par nom.
2. **Aucune valeur de secret** dans une structure persistée ou journalisée : seules des `SecretRef` (§6.3) existent.
3. **Compatibilité d'abord.** Les formats JSON existants (§10) restent lisibles ; toute évolution est versionnée (`schema_version`).
4. **Les contenus non fiables sont étiquetés** (`trust="untrusted"`) dès l'entrée ; ils ne portent jamais de pouvoir de décision.
5. **Dates** : ISO 8601 (`YYYY-MM-DDTHH:MM:SS`, heure locale) ; l'existant mémoire n'a que `YYYY-MM-DD` (conservé).

---

## 2. Outils

### 2.1 Déclaration d'outil envoyée au modèle **[ACTUEL]** (`core/tools.py`, 26 entrées)

Format inchangé en V1 (types en **majuscules** attendus par le SDK Gemini) :

```python
{
  "name": "file_controller",
  "description": "…",
  "parameters": {
    "type": "OBJECT",
    "properties": {"action": {"type": "STRING", "description": "…"}, "path": {"type": "STRING", "description": "…"}},
    "required": ["action"]
  }
}
```

### 2.2 `ToolSpec` **[V1]** (registre, C-08a)

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str                                 # unique ; identique à la déclaration modèle
    description: str
    parameters: dict                          # schéma identique à §2.1 (compatibilité)
    handler: str                              # "actions.open_app:open_app" (chemin dotté, import tardif)
    timeout_s: float = 30.0
    planner: bool = False                     # exposé au planificateur d'agent
    platforms: frozenset[str] = frozenset({"windows"})
    status_note: str | None = None            # ex. "simulation", "expérimental"
```

### 2.3 `ActionSpec` **[CIBLE V1.5]** (contrat d'action, C-08)

```python
@dataclass(frozen=True)
class ActionSpec(ToolSpec):
    params_model: type                        # dataclass typée des paramètres + validation
    capability: str                           # capacité requise ("filesystem", "browser", "ui_input", "messaging", "process", "network")
    risk: RiskLevel | Mapping[str, RiskLevel] # défaut ou surcharge par `action` (ex. file_controller.delete → HIGH)
    permissions: frozenset[str]               # ex. {"fs.write", "net.out"}
    requires_confirmation: Callable[[Mapping], bool] | bool = False
    side_effects: tuple[str, ...] = ()        # ex. ("filesystem", "external_message")
    reversible: bool = False                  # annulation/compensation possible
    compensate: str | None = None             # nom d'action de compensation
    idempotent: bool = False
    verify: str | None = None                 # chemin dotté du vérificateur (observation réelle)
    audit_fields: tuple[str, ...] = ()        # paramètres autorisés dans le journal (le reste masqué)
```

### 2.4 Appel et résultat

```python
class Origin(StrEnum): USER="user"; AUTONOMY="autonomy"; NOTIFICATION="notification"; MEMORY="memory"; SYSTEM="system"
class Verification(StrEnum): VERIFIED="verified"; UNVERIFIED="unverified"; NOT_APPLICABLE="not_applicable"
class ResultStatus(StrEnum): OK="ok"; UNVERIFIED="unverified"; ERROR="error"; DECLINED="declined"; CANCELLED="cancelled"

@dataclass(frozen=True)
class ToolCall:
    id: str; name: str; args: Mapping[str, Any]; origin: Origin = Origin.USER
    task_id: str | None = None; step_id: int | None = None

@dataclass(frozen=True)
class ToolResult:
    status: ResultStatus
    message: str                              # court, lisible, sans secret ; ≤ ~4 000 caractères
    data: Mapping[str, Any] | None = None
    error: ErrorCode | None = None
    verification: Verification = Verification.NOT_APPLICABLE
    duration_ms: int = 0
    trust: Literal["trusted", "untrusted"] = "trusted"   # "untrusted" pour tout contenu issu du web/fichiers/messages
```

Réponse au modèle en **V1** (compatibilité) : `{"result": message}` + champs additionnels `status`, `verified` (ignorables). Règle : un résultat vide d'action **n'est plus** « Done. » mais `ResultStatus.UNVERIFIED` avec message « terminé, non vérifié ».

### 2.5 `ErrorCode` (normatif)

```python
class ErrorCode(StrEnum):
    CONFIG_MISSING="config_missing"; AUTH_FAILED="auth_failed"; PROVIDER_UNAVAILABLE="provider_unavailable"
    NETWORK_DOWN="network_down"; CAPABILITY_MISSING="capability_missing"; RATE_LIMITED="rate_limited"
    VALIDATION_FAILED="validation_failed"; PERMISSION_DENIED="permission_denied"
    CONFIRMATION_DECLINED="confirmation_declined"; TIMEOUT="timeout"; CANCELLED="cancelled"
    PLATFORM_UNSUPPORTED="platform_unsupported"; DEPENDENCY_MISSING="dependency_missing"
    ACTION_FAILED="action_failed"; VERIFICATION_FAILED="verification_failed"
    BUDGET_EXCEEDED="budget_exceeded"; INTERNAL="internal"
```
Chaque code a un **message utilisateur** non technique et un **message de diagnostic** (journal). `retryable` : `NETWORK_DOWN`, `RATE_LIMITED`, `TIMEOUT`, `PROVIDER_UNAVAILABLE` (selon politique) ; **non retryable** : `VALIDATION_FAILED`, `PERMISSION_DENIED`, `CONFIRMATION_DECLINED`, `AUTH_FAILED`.

### 2.6 `ExecutionContext`

```python
@dataclass(frozen=True)
class ExecutionContext:
    origin: Origin; level: AutonomyLevel; task_id: str | None; step_id: int | None
    cancel: CancelToken; deadline: float | None; budget: Budget | None; ui: UiPort | None
```

---

## 3. Tâches, plans et exécution

### 3.1 Statuts et priorités

**[ACTUEL]** (`agent/task_queue.py`) :
```python
class TaskStatus(Enum): PENDING="pending"; RUNNING="running"; COMPLETED="completed"; FAILED="failed"; CANCELLED="cancelled"
class TaskPriority(Enum): LOW=3; NORMAL=2; HIGH=1      # plus petit = plus prioritaire
```

**[V1]** : ajout de `ABORTED="aborted"` et `PARTIAL="partial"` ; `COMPLETED` conservé comme **alias** de `SUCCEEDED` pour la compatibilité (lecture des anciens états) ; priorités inchangées.

**[CIBLE V1.5]** :
```python
class TaskStatus(StrEnum):
    PENDING="pending"; PLANNING="planning"; AWAITING_APPROVAL="awaiting_approval"; RUNNING="running"
    VERIFYING="verifying"; REPLANNING="replanning"; PAUSED="paused"; NEEDS_HELP="needs_help"
    SUCCEEDED="succeeded"; FAILED="failed"; CANCELLED="cancelled"          # terminaux : SUCCEEDED, FAILED, CANCELLED
class Priority(IntEnum): HIGH=1; NORMAL=2; LOW=3
```
Transitions autorisées : voir `APP_FLOW.md` F-09 (machine à états) ; toute autre transition est une erreur `INTERNAL`.

### 3.2 Plan et étapes

**[ACTUEL]** — JSON produit par `agent/planner.py` :
```json
{ "goal": "…", "steps": [ { "step": 1, "tool": "web_search", "description": "…", "parameters": {"query": "…"}, "critical": true } ] }
```
(≤ 5 étapes ; `generated_code` remplacé par `web_search` à la validation.)

**[CIBLE V1.5]** :
```python
@dataclass(frozen=True)
class ValueRef:                              # référence typée au résultat d'une étape précédente
    step: int; name: str

@dataclass(frozen=True)
class PlanStep:
    index: int                               # 1-based
    tool: str
    params: Mapping[str, Any | ValueRef]     # valeurs littérales ou ValueRef (jamais interpolation textuelle libre)
    description: str
    critical: bool = False
    produces: Mapping[str, str] = field(default_factory=dict)   # nom → type ("str","path","list[str]","int","bool","json")
    success_criteria: str | None = None      # lisible ; traduit en vérification par l'action
    retry: RetryPolicy | None = None         # sinon celle de l'action

@dataclass(frozen=True)
class Plan:
    goal: str; steps: tuple[PlanStep, ...]; created_at: str; planner_id: str; revision: int = 0
```
Validation d'un plan : voir C-09 (outil connu, paramètres valides, `ValueRef` pointant vers une étape **antérieure** qui `produces` ce nom avec un type compatible, ≤ 12 étapes, aucun `generated_code`).

### 3.3 Résultats d'étape et d'exécution

```python
class StepStatus(StrEnum): OK="ok"; UNVERIFIED="unverified"; SKIPPED="skipped"; FAILED="failed"; CANCELLED="cancelled"

@dataclass(frozen=True)
class StepResult:
    index: int; tool: str; status: StepStatus; attempts: int
    outputs: Mapping[str, Any] = field(default_factory=dict)       # valeurs produites (typées)
    message: str = ""; error: ErrorCode | None = None; verification: Verification = Verification.NOT_APPLICABLE
    started_at: str = ""; duration_ms: int = 0

class ExecutionStatus(StrEnum): SUCCEEDED="succeeded"; PARTIAL="partial"; FAILED="failed"; ABORTED="aborted"; CANCELLED="cancelled"

@dataclass(frozen=True)
class ExecutionResult:                         # V1 et V1.5
    status: ExecutionStatus; steps: tuple[StepResult, ...]; summary: str      # le résumé reprend les statuts réels
    error: ErrorCode | None = None; replans: int = 0
```
Règle de cohérence : `SUCCEEDED` ⇔ toutes les étapes `critical` sont `OK|UNVERIFIED` et aucune n'est `FAILED` ; `PARTIAL` si des étapes non critiques sont `SKIPPED|FAILED` ; `ABORTED` si l'arrêt vient d'une décision `ABORT`.

### 3.4 Reprise sur erreur

**[ACTUEL]** `ErrorDecision(Enum)`: `RETRY, SKIP, REPLAN, ABORT` (décision produite par un LLM, avec `max_attempts=2` par défaut — cause du plafond effectif de 2 tentatives, R-O12).

**[CIBLE V1.5]** :
```python
@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3                         # tentatives par étape (V1 : 3 réelles)
    backoff_s: tuple[float, ...] = (1.0, 3.0)     # attentes entre tentatives
    retry_on: frozenset[ErrorCode] = frozenset({ErrorCode.TIMEOUT, ErrorCode.NETWORK_DOWN, ErrorCode.RATE_LIMITED, ErrorCode.PROVIDER_UNAVAILABLE})
    replan_on: frozenset[ErrorCode] = frozenset({ErrorCode.VALIDATION_FAILED, ErrorCode.VERIFICATION_FAILED, ErrorCode.ACTION_FAILED})
    ask_help_on: frozenset[ErrorCode] = frozenset({ErrorCode.PERMISSION_DENIED, ErrorCode.CONFIRMATION_DECLINED, ErrorCode.CONFIG_MISSING})
    abort_on: frozenset[ErrorCode] = frozenset({ErrorCode.AUTH_FAILED, ErrorCode.BUDGET_EXCEEDED})

@dataclass(frozen=True)
class Budget:
    max_duration_s: float = 600; max_steps: int = 12; max_replans: int = 2
    max_model_calls: int | None = 40; max_cost_usd: float | None = None     # seulement si le provider expose le coût
```
`ErrorDecision` LLM devient **consultatif** : la politique déclarative prime ; un `ABORT` du modèle n'annule jamais une tâche **sans journaliser** la raison.

### 3.5 `TaskState` (suivi, reprise, annulation)

```python
@dataclass
class TaskState:
    task_id: str; goal: str; origin: Origin; priority: Priority
    status: TaskStatus; plan: Plan | None; current_step: int
    results: list[StepResult]; budget: Budget; budget_used: BudgetUsage
    created_at: str; updated_at: str; finished_at: str | None
    cancel_requested: bool = False; pause_requested: bool = False
    error: ErrorCode | None = None; summary: str = ""
    pending_confirmation: ConfirmationRequest | None = None
    schema_version: int = 1
```
**Persistance (V1.5, P15)** — `tasks.db` (SQLite, hors dépôt) :
```sql
CREATE TABLE tasks(task_id TEXT PRIMARY KEY, goal TEXT NOT NULL, origin TEXT NOT NULL, priority INTEGER NOT NULL,
  status TEXT NOT NULL, plan_json TEXT, current_step INTEGER NOT NULL DEFAULT 0, budget_json TEXT NOT NULL,
  budget_used_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, finished_at TEXT,
  cancel_requested INTEGER NOT NULL DEFAULT 0, pause_requested INTEGER NOT NULL DEFAULT 0,
  error TEXT, summary TEXT NOT NULL DEFAULT '', schema_version INTEGER NOT NULL DEFAULT 1);
CREATE TABLE task_steps(task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE, idx INTEGER NOT NULL,
  tool TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL, outputs_json TEXT, message TEXT, error TEXT,
  verification TEXT, started_at TEXT, duration_ms INTEGER, PRIMARY KEY(task_id, idx));
```
Reprise après redémarrage : tâches `RUNNING|VERIFYING|REPLANNING` → `PAUSED` ; jamais relancées automatiquement sans règle explicite.

---

## 4. Autonomie, risques et permissions

```python
class AutonomyLevel(StrEnum): OFF="off"; ASSISTED="assisted"; SUPERVISED="supervised"; AUTONOMOUS="autonomous"
class RiskLevel(IntEnum): LOW=1; MEDIUM=2; HIGH=3; CRITICAL=4
class Decision(StrEnum): ALLOW="allow"; CONFIRM="confirm"; DENY="deny"

@dataclass(frozen=True)
class Scope:                                    # périmètre autorisé en AUTONOMOUS / SUPERVISED (défini par l'utilisateur)
    tools: frozenset[str] = frozenset(); path_roots: tuple[Path, ...] = ()
    recipients: frozenset[str] = frozenset()    # "plateforme:contact"
    domains: frozenset[str] = frozenset()
    max_actions_per_hour: int = 30

@dataclass(frozen=True)
class PermissionDecision:
    decision: Decision; reason: str; risk: RiskLevel; rule_id: str; requires_scope: bool = False

@dataclass(frozen=True)
class ConfirmationRequest:                     # voir C-12
    request_id: str; action: str; summary: str; risk: RiskLevel; origin: Origin
    effects: tuple[str, ...]; reversible: bool; preview: str | None = None; timeout_s: float = 30.0

class ConfirmationDecision(StrEnum): APPROVED="approved"; DECLINED="declined"; EXPIRED="expired"
```
`Trigger` / `TriggerEvent` (autonomie) : `Trigger(id, kind ∈ {schedule,event,notification,idea}, condition, goal_template, priority, min_level, cooldown_s, enabled)` ; `TriggerEvent(trigger_id, payload: untrusted, fired_at)`. L'ancien `Idea` (`core/autonomy_manager.py`) est **converti** en `Trigger(kind="idea")` ; l'ancienne `sensitivity` (entier 1–10, défaut 5) devient un **seuil de déclenchement**.

Interdictions fondamentales : voir `BACKEND_CONTRACT.md` C-13 (liste normative, non dupliquée ici).

---

## 5. Événements de journalisation

**[ACTUEL]** `logs/action_history.jsonl` (`ActionLogger.log`, **seulement `interact_ui`**) :
```json
{"timestamp": "2026-01-01T12:00:00", "action": "click", "target_name": "Bouton OK", "target_coords": {"x": 100, "y": 200}, "value": null, "success": true}
```
`value` est renseigné quand `action == "type"` (**contenu saisi** — supprimé en P7). Un second fichier `logs/autonomy_audit.jsonl` est prévu par `log_autonomy` mais **jamais alimenté**.

**[CIBLE V1.5]** :
```python
@dataclass(frozen=True)
class AuditEvent:
    ts: str; level: Literal["debug","info","warn","error"]; event: str      # "tool.end", "permission.decision", "task.transition", …
    task_id: str | None = None; step_id: int | None = None; tool: str | None = None
    origin: Origin | None = None; status: str | None = None; error: ErrorCode | None = None
    duration_ms: int | None = None; verification: Verification | None = None
    params_redacted: Mapping[str, Any] | None = None       # uniquement les champs de ActionSpec.audit_fields
    provider_id: str | None = None; extra: Mapping[str, Any] = field(default_factory=dict)
```
Règles : **jamais** de secret, texte tapé, contenu de message, contenu de capture ; l'événement de capture porte `{app, w, h, filtered: bool}` seulement.

---

## 6. Providers

### 6.1 Capacités déclarées

```python
class Capability(StrEnum):
    TEXT_GENERATION="text_generation"; STRUCTURED_OUTPUT="structured_output"; TEXT_STREAMING="text_streaming"
    TOOL_CALLS="tool_calls"; REALTIME_VOICE="realtime_voice"; AUDIO_INPUT="audio_input"; AUDIO_OUTPUT="audio_output"
    TRANSCRIPTION="transcription"; SPEECH_SYNTHESIS="speech_synthesis"; WAKE_WORD="wake_word"
    EMBEDDINGS="embeddings"; VISION="vision"; INTERRUPTIONS="interruptions"
```

```python
class ProviderKind(StrEnum): CLOUD="cloud"; LOCAL="local"

@dataclass(frozen=True)
class ProviderCapabilities:
    provider_id: str; kind: ProviderKind
    capabilities: frozenset[Capability]                       # Capability : voir C-02
    languages: frozenset[str] | None = None                   # None = inconnu (non supposé)
    max_context_tokens: int | None = None; max_output_tokens: int | None = None
    rate_limit_per_min: int | None = None; est_cost_per_1k_tokens_usd: float | None = None
    requires_network: bool = True; requires_secret: str | None = None      # nom de variable, jamais la valeur
    min_ram_gb: float | None = None; needs_gpu: bool | None = None         # providers locaux
    notes: tuple[str, ...] = ()
```
**Règle** : un champ à `None` signifie « inconnu » et **n'autorise aucune hypothèse**.

### 6.2 Configuration non secrète d'un provider

```python
@dataclass
class ProviderConfig:
    provider_id: str; enabled: bool = True
    role: Literal["text","realtime_voice","stt","tts","embeddings","wake_word"]
    model: str | None = None                      # nom de modèle (config, pas constante)
    api_version: str | None = None                # ex. version d'API du service vocal (ADR-022)
    endpoint: str | None = None                   # ex. hôte local (non secret)
    options: Mapping[str, Any] = field(default_factory=dict)
    secret: SecretRef | None = None
    allow_remote: bool = False                    # consentement explicite d'envoi de données
```

### 6.3 `SecretRef`

```python
@dataclass(frozen=True)
class SecretRef:
    name: str                                     # ex. "GEMINI_API_KEY"
    source: Literal["env", "dotenv_profile", "dotenv_project", "credential_manager"]
    present: bool                                 # calculé à la lecture ; JAMAIS la valeur
```
Une `SecretRef` est sérialisable ; elle ne contient **ni valeur ni empreinte** de la valeur.

### 6.4 Routage

```python
@dataclass(frozen=True)
class RoutingRequest:
    required: frozenset[Capability]; mode: Literal["cloud","local","mixed"]
    allow_remote: Mapping[Capability, bool]; fallback: Literal["none","local","cloud"] = "none"
    prefer_low_cost: bool = False; max_latency_ms: int | None = None
@dataclass(frozen=True)
class RoutingDecision:
    provider_id: str; reason: str; fallbacks: tuple[str, ...]; warnings: tuple[str, ...] = ()
@dataclass(frozen=True)
class HealthStatus:
    ok: bool; detail: str = ""; latency_ms: int | None = None; checked_at: str = ""
```

### 6.5 Messages vocaux temps réel (extrait)

`RealtimeSessionConfig(model, api_version, voice, system_instruction, tools: list[ToolSpec], transcription_in: bool, transcription_out: bool, resumption: bool)` ; `RealtimeEvent = AudioChunk(pcm: bytes, rate: int) | Transcript(role, text, final: bool) | ToolCallRequest(call: ToolCall) | TurnComplete | Interrupted | Error(code: ErrorCode, detail: str)`. Formats audio **existants** : entrée PCM int16 mono 16 000 Hz (blocs de 1 024 échantillons) ; sortie PCM 24 000 Hz.

---

## 7. Configuration, secrets et chemins

### 7.1 Variables d'environnement / `.env` **[V1]**

```dotenv
# .env.example — noms et valeurs FACTICES uniquement
GEMINI_API_KEY=your_key_here
```
Règles : une ligne `NOM=valeur` par secret ; la réécriture d'une clé **préserve** les autres lignes et commentaires ; variable d'environnement **prioritaire** ; `JARVIS_MEMORY_DIR` (surcharge de dossier, usage **test** uniquement) n'est pas un secret.

### 7.2 `settings.json` **[V1]** (non secret)

```json
{
  "schema_version": 1,
  "os_system": "windows",
  "allow_generated_desktop_code": false,
  "confirm_sensitive": true
}
```
`os_system ∈ {"windows","mac","linux"}` (valeurs actuelles de l'UI ; seul `windows` est **supporté**). `SettingsStore.save` **refuse** toute clé dont le nom contient `key`, `secret`, `token`, `password`.

**[CIBLE V1.5]** extension :
```json
{
  "schema_version": 2,
  "provider": {"mode": "cloud", "fallback": "none",
               "roles": {"text": "gemini", "realtime_voice": "gemini_live", "stt": null, "tts": null, "embeddings": null},
               "allow_remote": {"text": true, "realtime_voice": true, "embeddings": false}},
  "autonomy": {"level": "off", "scope": {"tools": [], "path_roots": [], "recipients": [], "domains": []},
               "budget": {"max_duration_s": 600, "max_steps": 12, "max_replans": 2, "max_model_calls": 40}},
  "rag": {"enabled": false, "allowed_roots": [], "embeddings": "off"}
}
```

### 7.3 `Paths`

```python
@dataclass(frozen=True)
class Paths:
    root: Path; config_dir: Path; memory_dir: Path; logs_dir: Path; secrets_env: Path; projects_dir: Path   # dev vs installé
```

### 7.4 Formats historiques (à migrer/lire en lecture seule)

| Fichier | Format actuel | Devenir |
|---|---|---|
| `ui/config/api_keys.json` (**tracé par Git**) et `config/api_keys.json` (ignoré) | `{"gemini_api_key": "<secret>", "os_system": "windows"}` | **Secret → `.env`** (P1) ; `os_system` → `settings.json` ; ancien fichier **supprimé après migration** par l'utilisateur ; jamais relu après P1 sauf drapeau temporaire `JARVIS_LEGACY_CONFIG` |
| `config/app_profiles.json` | `blocked{processes[], title_patterns[]}`, `browser{processes[], cdp_port}`, `vision_only{processes[], title_patterns[]}`, `capture{interval_seconds, width, height, jpeg_quality, diff_enabled}`, `privacy{blur_password_fields, confirm_critical_actions}` | **Conservé** ; `confirm_critical_actions` enfin **lu** (P7) ; extension V1.5 : `allowed_domains`, `blocked_domains` |
| `config/notifications_config.json` | `{enabled, allowed_apps[], auto_reply_enabled, rules[{app, sender, action}]}` | **Conservé** ; `auto_reply_enabled` passe à `false` par défaut (P7) |

---

## 8. Mémoire

### 8.1 Format **[ACTUEL]** — `memory/long_term.json`

```json
{
  "identity":      {"name": {"value": "Alex", "updated": "2026-01-01"}},
  "preferences":   {}, "projects": {}, "routines": {}, "context": {},
  "skills":        {}, "relationships": {}, "wishes": {}, "notes": {}
}
```
- Catégories (9) : `identity, preferences, projects, routines, context, skills, relationships, wishes, notes`.
- Entrée : `{"value": str (≤ 380 car.), "updated": "YYYY-MM-DD"}` ; plafond global 8 000 caractères (élagage des plus anciennes, signalé par `print` console).
- Fichiers dérivés **régénérés** à chaque sauvegarde (jamais relus) : `USER_IDENTITY.md, USER_PREFERENCES.md, USER_PROJECTS.md, USER_ROUTINES.md, USER_CONTEXT.md, USER_SKILLS.md, USER_RELATIONS.md` (7 catégories ; **`wishes` et `notes` non exportées**).
- Sauvegarde : `long_term.json.bak` ; écriture par fichier temporaire puis remplacement.

### 8.2 Modèles **[CIBLE V1.5]**

```python
class MemoryCategory(StrEnum):
    IDENTITY="identity"; PREFERENCES="preferences"; PROJECTS="projects"; ROUTINES="routines"; CONTEXT="context"
    SKILLS="skills"; RELATIONSHIPS="relationships"; WISHES="wishes"; NOTES="notes"

@dataclass(frozen=True)
class MemoryEntry:
    category: MemoryCategory; key: str; value: str
    created_at: str; updated_at: str
    origin: Origin                                  # qui a écrit (user/system/autonomy…)
    source_ref: str | None = None                   # provenance (ex. "conversation:2026-01-01", "migrated:long_term.json")
    sensitivity: Literal["normal","sensitive"] = "normal"
    trust: Literal["trusted","untrusted"] = "untrusted"    # le contenu rappelé est une DONNÉE
    deleted_at: str | None = None                   # suppression logique avant purge

@dataclass(frozen=True)
class MemoryWrite: category: str; key: str; value: str; origin: Origin; source_ref: str | None = None
@dataclass(frozen=True)
class PromptMemory: text: str; included: tuple[tuple[str, str], ...]; truncated: bool      # clés incluses, pour traçabilité
```

### 8.3 Stockage SQLite **[CIBLE V1.5, P17]** — `memory.db`

Cas d'usage servis : (1) mémoire **structurée** (préférences, identité, projets, routines…), (2) **épisodique** (événements de conversations/tâches **explicitement retenus**), (3) recherche lexicale ; le RAG documentaire est au §9.

```sql
PRAGMA journal_mode = WAL;
CREATE TABLE schema_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);           -- ('schema_version','1'), ('migrated_from','long_term.json')

CREATE TABLE memory_entries(
  id INTEGER PRIMARY KEY,
  category TEXT NOT NULL CHECK(category IN ('identity','preferences','projects','routines','context','skills','relationships','wishes','notes')),
  key TEXT NOT NULL, value TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  origin TEXT NOT NULL DEFAULT 'user', source_ref TEXT,
  sensitivity TEXT NOT NULL DEFAULT 'normal' CHECK(sensitivity IN ('normal','sensitive')),
  deleted_at TEXT,
  UNIQUE(category, key));

CREATE TABLE memory_episodes(                                                 -- épisodique : retenu explicitement, jamais automatique pour audio/écran
  id INTEGER PRIMARY KEY, occurred_at TEXT NOT NULL, kind TEXT NOT NULL,       -- 'conversation_summary' | 'task_outcome'
  summary TEXT NOT NULL, task_id TEXT, source_ref TEXT, sensitivity TEXT NOT NULL DEFAULT 'normal', deleted_at TEXT);

CREATE VIRTUAL TABLE memory_fts USING fts5(key, value, content='memory_entries', content_rowid='id');
CREATE TRIGGER memory_ai AFTER INSERT ON memory_entries BEGIN
  INSERT INTO memory_fts(rowid, key, value) VALUES (new.id, new.key, new.value); END;
CREATE TRIGGER memory_ad AFTER DELETE ON memory_entries BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, key, value) VALUES ('delete', old.id, old.key, old.value); END;
CREATE TRIGGER memory_au AFTER UPDATE ON memory_entries BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, key, value) VALUES ('delete', old.id, old.key, old.value);
  INSERT INTO memory_fts(rowid, key, value) VALUES (new.id, new.key, new.value); END;
```

### 8.4 Migration `long_term.json` → `memory.db` et retour arrière

| Étape | Règle |
|---|---|
| 0. Sauvegarde | copie horodatée de `long_term.json`, `long_term.json.bak`, `USER_*.md` **hors dépôt** |
| 1. Lecture | refus si JSON illisible (restauration préalable depuis `.bak` valide) |
| 2. Transformation | pour chaque `category/key` : `value` ← `value` ; `updated_at` ← `updated` (date → `YYYY-MM-DDT00:00:00`) ; `created_at` ← `updated_at` ; `origin='system'` ; `source_ref='migrated:long_term.json'` ; `sensitivity='normal'` ; **catégorie inconnue** ⇒ `notes` avec préfixe de clé `legacy_<cat>_` et avertissement |
| 3. Vérification | `COUNT` par catégorie égal à la source ; `PRAGMA integrity_check` = `ok` ; relecture d'un échantillon ; régénération des `USER_*.md` **identique** (comparaison de contenu) |
| 4. Bascule | `memory_manager` lit la base ; `long_term.json` **conservé** jusqu'à validation (ADR-020) |
| Retour arrière | `python -m memory.migrate --rollback` : restaure la sauvegarde de l'étape 0 et repasse le drapeau de lecture sur JSON ; option `--export-json` régénère `long_term.json` depuis la base (en respectant les plafonds historiques ; les entrées au-delà sont listées, pas supprimées) |
| Compatibilité | les interfaces `load_memory()/update_memory()/remember()` restent disponibles (adaptateur au-dessus du service) ; `format_memory_for_prompt` conserve ses limites (2 000 caractères ; plafonds par catégorie) |

---

## 9. RAG local (provenance, mise à jour, suppression) **[CIBLE V1.5, P18]**

### 9.1 Modèles

```python
class SourceKind(StrEnum): FOLDER="folder"; FILE="file"; DROPPED_FILE="dropped_file"; CONVERSATION_NOTE="conversation_note"

@dataclass(frozen=True)
class IndexPolicy:                                # règle d'indexation explicite (aucun défaut implicite)
    allowed_extensions: frozenset[str]; recursive: bool; max_file_bytes: int
    exclude_globs: tuple[str, ...]; embeddings: Literal["off","local","remote_with_consent"]; retention_days: int | None

@dataclass(frozen=True)
class IngestSource: kind: SourceKind; uri: str; display_name: str; consent_at: str          # horodatage du consentement

@dataclass(frozen=True)
class SearchHit:
    chunk_id: int; source_id: str; document_id: str; score: float                      # 0..1 après normalisation
    score_parts: Mapping[str, float]                                                    # {"lexical":…, "vector":…} (diagnostic)
    start_offset: int; end_offset: int; excerpt: str; trust: Literal["untrusted"] = "untrusted"

@dataclass(frozen=True)
class RetrievalResult: hits: tuple[SearchHit, ...]; mode_used: Literal["lexical","vector","hybrid"]; warnings: tuple[str, ...]
@dataclass(frozen=True)
class IngestReport: source_id: str; documents: int; chunks: int; skipped: tuple[tuple[str, str], ...]; failed: tuple[tuple[str, str], ...]
```

### 9.2 Tables (dans `memory.db`)

```sql
CREATE TABLE sources(
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, uri TEXT NOT NULL, display_name TEXT NOT NULL,
  policy_json TEXT NOT NULL, consent_at TEXT NOT NULL, added_at TEXT NOT NULL,
  last_indexed_at TEXT, status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','indexed','failed','removed')), error TEXT);

CREATE TABLE documents(
  id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  path TEXT NOT NULL, mime TEXT, size_bytes INTEGER, modified_at TEXT,
  content_hash TEXT NOT NULL,                       -- mise à jour : réindexer seulement si le hash change
  indexed_at TEXT, status TEXT NOT NULL DEFAULT 'indexed', error TEXT,
  UNIQUE(source_id, path));

CREATE TABLE chunks(
  id INTEGER PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL, text TEXT NOT NULL,
  start_offset INTEGER NOT NULL, end_offset INTEGER NOT NULL,   -- provenance précise dans le document
  token_estimate INTEGER, content_hash TEXT NOT NULL, meta_json TEXT,
  UNIQUE(document_id, ordinal));

CREATE VIRTUAL TABLE chunks_fts USING fts5(text, content='chunks', content_rowid='id');
-- triggers chunks_ai / chunks_ad / chunks_au analogues à memory_* (§8.3)

CREATE TABLE embeddings(                              -- FACULTATIF ; table absente tant que les embeddings sont "off"
  chunk_id INTEGER PRIMARY KEY REFERENCES chunks(id) ON DELETE CASCADE,
  model_id TEXT NOT NULL, dim INTEGER NOT NULL, vector BLOB NOT NULL, created_at TEXT NOT NULL);
```

### 9.3 Règles de provenance, mise à jour et suppression

| Besoin | Règle |
|---|---|
| **Provenance** | toute citation renvoie `source_id → document.path → chunk.start_offset:end_offset` + `content_hash` ; le contexte transmis au modèle liste les sources |
| **Mise à jour** | comparer `documents.content_hash` ; si changé : supprimer les `chunks` du document (cascade FTS/vecteurs), réindexer ; si absent du disque : `status='removed'` puis purge |
| **Suppression** | `delete_source(id)` ⇒ `ON DELETE CASCADE` sur `documents`, `chunks`, `embeddings` + `INSERT … 'delete'` FTS via triggers ; retourne le nombre de segments supprimés ; test : plus aucun `chunk` ne référence la source |
| **Récupération** | lexical (FTS5, `bm25`) puis, si activé, vectoriel ; fusion + classement ; sélection sous budget de caractères ; encapsulation `untrusted` |
| **Consentement** | une source sans `consent_at` ne peut pas être créée ; `embeddings="remote_with_consent"` exige un consentement distinct horodaté (`settings.rag`) |
| **Exclusions** | audio, captures d'écran, messages : **jamais** indexés par défaut (aucune `SourceKind` correspondante) |
| **Reconstruction** | l'index est **dérivé** : supprimer `chunks_fts`/`embeddings` puis réindexer depuis les `sources` doit redonner un état équivalent |

---

## 10. Interface (événements) — extrait des types référencés

```python
class SessionState(StrEnum):    # états HUD (existants + V1/V1.5)
    NOT_CONFIGURED="not_configured"; CONNECTING="connecting"; LISTENING="listening"; THINKING="thinking"
    SPEAKING="speaking"; MUTED="muted"; OFFLINE="offline"; ERROR="error"
    # mapping vers les états UI existants : INITIALISING↔CONNECTING, PROCESSING↔THINKING(outil)
UiEvent = StateChanged | LogLine | ErrorShown | TaskUpdated | ConfirmationRequested | ProviderStatus | AutonomyLevelChanged | CaptureIndicator
```
Aucun type d'événement ne transporte de secret ; `LogLine(text, tag)` reprend les étiquettes existantes du `LogWidget` (`you`, `ai`, `sys`, `err`).

---

## 11. Cohérence avec `BACKEND_CONTRACT.md`

| Contrat | Types définis ici |
|---|---|
| C-01 | `SessionState`, `Origin` |
| C-02…C-07 | `ProviderCapabilities`, `ProviderConfig`, `SecretRef`, `RoutingRequest/Decision`, `HealthStatus`, `RealtimeSessionConfig/Event` |
| C-08 | `ToolSpec`, `ActionSpec`, `ToolCall`, `ToolResult`, `ErrorCode`, `ExecutionContext` |
| C-09 | `Plan`, `PlanStep`, `ValueRef` |
| C-10 | `TaskStatus`, `Priority`, `TaskState`, `StepResult`, `ExecutionResult`, `RetryPolicy`, `Budget` |
| C-11 | `Trigger`, `TriggerEvent`, `AutonomyLevel` |
| C-12, C-13 | `ConfirmationRequest/Decision`, `RiskLevel`, `Decision`, `Scope`, `PermissionDecision` |
| C-14 | `Settings` (§7), `Paths`, `SecretRef` |
| C-15 | `MemoryEntry`, `MemoryWrite`, `PromptMemory`, DDL §8 |
| C-16 | `AuditEvent` |
| C-17 | `SessionState`, `UiEvent`, `UiCommand` |
| C-19 | `IndexPolicy`, `IngestSource`, `SearchHit`, `RetrievalResult`, DDL §9 |
