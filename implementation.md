# JARVIS AGI — ROADMAP COMPLÈTE

# Autonomous General Intelligence — Python Implementation

# Version : 1.1 | Statut : Architecture Blueprint

# Changelog v1.1 : +Goal Conflict Resolver | +Deep Self-Correction | +Deep Environment Awareness | +Claude↔Jarvis AI Protocol

---

```
                    ┌─────────────────────────────────────────┐
                    │              JARVIS AGI CORE            │
                    │                                         │
                    │  PERCEPTION → COGNITION → ACTION LOOP   │
                    │                                         │
                    │  "Observe. Think. Decide. Act. Learn."  │
                    └─────────────────────────────────────────┘
```

---

## TABLE DES MATIÈRES

```
01. PERCEPTION LAYER              → Comment Jarvis perçoit le monde
    └── 1.5 [NEW] Deep Environment Awareness
02. MEMORY SYSTEM                 → Comment Jarvis stocke et rappelle
03. COGNITION ENGINE              → Comment Jarvis pense et planifie
    └── 3.5 [NEW] Goal Conflict Resolver
04. ACTION LAYER                  → Ce que Jarvis peut faire
05. AUTONOMY ENGINE               → Comment Jarvis agit seul
06. LEARNING LOOP                 → Comment Jarvis s'améliore
    └── 6.4 [NEW] Deep Self-Correction Engine
07. SELF-MONITORING               → Comment Jarvis se surveille lui-même
08. SECURITY & PRIVACY            → Limites et garde-fous
09. TECH STACK & ARCHITECTURE     → Structure du projet Python
10. [NEW] CLAUDE ↔ JARVIS PROTOCOL → Dialogue AI-to-AI pour l'autonomie
```

---

# 01. PERCEPTION LAYER

> _Comment Jarvis perçoit le monde autour de lui_

## 1.1 — Voice Input (Speech-to-Text)

**Description** : Jarvis écoute en permanence (wake word) et transcrit la voix en texte.

**Flow** :

```
[Microphone stream]
        │
        ▼
[Wake word detection]  ──── "Hey Jarvis" ──── TRIGGER
        │
        ▼
[Audio buffer capture]  (enregistre jusqu'au silence ~1.5s)
        │
        ▼
[STT Engine]  →  Whisper local (whisper.cpp) ou Google STT
        │
        ▼
[Text normalization]  →  nettoyage, ponctuation, langue détectée
        │
        ▼
[Cognition Engine]  →  traitement de la requête
```

**Libs Python** :

```python
# Wake word
pvporcupine          # Porcupine wake word (Picovoice)
pyaudio              # Audio stream

# STT
openai-whisper       # Whisper local (offline)
google-cloud-speech  # Google STT (online, plus rapide)
faster-whisper       # Version optimisée de Whisper

# Audio utils
sounddevice
numpy
```

**Modes** :

- `ALWAYS_ON` : écoute permanente avec wake word
- `PUSH_TO_TALK` : raccourci clavier (ex: Ctrl+Space)
- `AUTO` : bascule selon l'activité système détectée

---

## 1.2 — Vision / Screen Awareness

**Description** : Jarvis voit l'écran, comprend le contenu visuel, identifie le contexte applicatif.

**Flow** :

```
[Trigger: "Jarvis, regarde ça" / screenshot auto / scheduled]
        │
        ▼
[Screen capture]  →  mss (multi-monitor support)
        │
        ▼
[App context detection]  →  quel process est au premier plan ?
        │
        ▼
[Vision LLM]  →  GPT-4o Vision / Claude Vision / Gemini Vision
        │
        ├──── [Text extraction]  →  OCR si document/code
        ├──── [UI understanding]  →  "il est sur Cursor, fichier routes.py"
        ├──── [Error detection]  →  "je vois une erreur TypeScript à la ligne 42"
        └──── [Content analysis]  →  "c'est un dashboard Analytics"
        │
        ▼
[Structured context]  →  injecté dans USER_CONTEXT.md
```

**Libs Python** :

```python
mss                   # Screenshot cross-platform
Pillow                # Image processing
pytesseract           # OCR local
psutil                # Process/window detection
pygetwindow           # Active window info
anthropic             # Claude Vision API
```

**Vision Events** :

- `on_demand` : l'utilisateur demande explicitement
- `on_error` : détection d'une fenêtre d'erreur système
- `on_focus_change` : changement d'application majeur
- `scheduled` : capture toutes les N minutes (mode surveillance)

---

## 1.3 — System Awareness

**Description** : Jarvis comprend l'état du système (CPU, RAM, réseau, batterie, heure).

**Flow** :

```
[Background daemon — polling toutes les 30s]
        │
        ▼
[System snapshot]
        ├── CPU usage, RAM, disk
        ├── Battery level + charging
        ├── Network (speed, connected/offline)
        ├── Active processes
        ├── Current time + timezone
        └── Calendar events (via Google Calendar API)
        │
        ▼
[Anomaly detection]
        ├── CPU > 90% pendant > 2min  →  alerte
        ├── Battery < 15%             →  alerte
        ├── Réseau coupé              →  mode offline
        └── Rappel calendrier dans    →  notification proactive
            15min
        │
        ▼
[Inject into USER_CONTEXT.md]  →  "batterie à 12%, pas connecté au secteur"
```

**Libs Python** :

```python
psutil               # CPU, RAM, battery, processes
speedtest-cli        # Network speed
schedule             # Polling scheduler
google-api-python-client  # Google Calendar
```

---

## 1.5 — Deep Environment Awareness [NEW — v1.1]

> _Critique Jarvis : "System Awareness est basique. L'autonomie totale nécessite une compréhension dynamique de l'intégralité de la machine."_

**Description** : Jarvis ne lit plus seulement CPU/RAM toutes les 30s. Il maintient un **modèle dynamique vivant** de l'environnement machine complet — processes, flux réseau, comportements utilisateur, charge applicative — et prend des décisions d'optimisation en temps réel sans supervision.

**Flow — Machine Model Builder** :

```
[Daemon permanent — event-driven, pas de polling fixe]
        │
        ▼
[Layer 1 — Hardware State]
        ├── CPU par core (pas seulement global)
        ├── RAM : utilisée / cache / swap
        ├── Disk I/O : lecture / écriture en cours
        ├── GPU (si disponible) : utilisation + VRAM
        ├── Température des composants
        └── Battery : drain rate, estimation autonomie restante
        │
        ▼
[Layer 2 — Process Intelligence]
        ├── Top 10 processes par consommation
        ├── Nouveaux processes lancés (delta depuis dernier snapshot)
        ├── Processes zombies / bloqués
        ├── Ports réseau ouverts + applications associées
        └── Fichiers verrouillés (lock contention)
        │
        ▼
[Layer 3 — Network Intelligence]
        ├── Interfaces actives (WiFi, Ethernet, VPN)
        ├── Latence vers les APIs critiques (Anthropic, OpenAI, GitHub)
        ├── Bande passante consommée par process
        ├── Connexions sortantes suspectes (anomaly detection)
        └── Mode offline → basculer sur modèles locaux automatiquement
        │
        ▼
[Layer 4 — User Behavior Model]
        ├── Application active + durée d'usage
        ├── Idle time (inactivité clavier/souris)
        ├── Fréquence de switching entre apps
        ├── Heure et corrélation avec USER_ROUTINES.md
        └── "Deep work signal" : même app > 20min sans switch
        │
        ▼
[Machine Model]  →  objet Python vivant, mis à jour en continu
        │
        ▼
[Autonomous Optimizer]
        ├── CPU > 85% + Jarvis non-urgent  →  baisser sa propre priorité (nice +5)
        ├── RAM critique + modèle cloud dispo  →  décharger le modèle local
        ├── Réseau lent  →  passer en mode réponse courte + cache agressif
        ├── Deep work signal  →  suspendre toutes notifications non-critiques
        ├── Batterie < 20% + pas de secteur  →  mode économie (désactiver vision + wake word)
        └── GPU libre + tâche vision en attente  →  prioritiser le traitement GPU
        │
        ▼
[Self-Report]  →  mise à jour USER_CONTEXT.md + log dans machine_state.json
```

**Structure Python** :

```python
@dataclass
class MachineModel:
    # Hardware
    cpu_per_core: list[float]
    ram: RamState           # used / cache / swap / total
    disk_io: DiskIO         # read_bytes/s, write_bytes/s
    gpu: GpuState | None
    temperatures: dict[str, float]
    battery: BatteryState   # level, plugged, drain_rate, eta_minutes

    # Processes
    top_processes: list[ProcessInfo]
    new_processes: list[str]      # delta depuis dernier snapshot
    zombie_processes: list[int]   # PIDs bloqués

    # Network
    active_interfaces: list[NetworkInterface]
    api_latencies: dict[str, float]   # ms par endpoint critique
    bandwidth_per_process: dict[str, float]
    is_online: bool

    # User Behavior
    active_app: str
    idle_seconds: int
    deep_work_signal: bool    # même app > 20min
    last_switch: datetime

    # Jarvis Meta
    jarvis_cpu_priority: int
    jarvis_memory_usage_mb: float
    last_updated: datetime


class AutonomousOptimizer:
    def evaluate(self, model: MachineModel) -> list[OptimizationAction]:
        """
        Évalue le machine model et retourne les actions d'optimisation
        à exécuter sans intervention de l'utilisateur.
        """

    def apply(self, action: OptimizationAction):
        """Exécute l'action : renice, swap modèle, suspendre modules..."""

    def log(self, action: OptimizationAction, reason: str):
        """Log dans /memory/logs/optimizer.log"""
```

**Libs Python** :

```python
psutil               # Base hardware + processes
GPUtil               # GPU monitoring
py-cpuinfo           # CPU détaillé
scapy                # Network packet analysis (avancé)
netaddr              # IP/network utilities
```

---

## 1.4 — File & Clipboard Watcher

**Description** : Jarvis surveille les modifications de fichiers importants et le presse-papier.

**Flow** :

```
[Watchdog daemon]  →  surveille /memory/, /projects/, desktop
        │
        ▼
[File event]  →  CREATE / MODIFY / DELETE
        │
        ▼
[Relevance filter]  →  est-ce un fichier que Jarvis connaît ?
        │
        ▼
[Auto-index]  →  met à jour sa représentation interne du projet

[Clipboard monitor]  →  polling toutes les 2s
        │
        ▼
[Content detection]
        ├── URL copiée      →  proposer résumé / analyse
        ├── Code copié      →  proposer review
        ├── Erreur copiée   →  proposer solution immédiate
        └── Texte normal    →  inactif
```

**Libs Python** :

```python
watchdog             # File system events
pyperclip            # Clipboard access
```

---

# 02. MEMORY SYSTEM

> _Comment Jarvis stocke, retrouve et enrichit sa mémoire_

## 2.1 — Short-Term Memory (Session RAM)

**Description** : Mémoire de la conversation en cours. Disparaît à la fin de session.

**Structure Python** :

```python
class ShortTermMemory:
    conversation_history: list[dict]   # Messages échangés
    current_task: str | None           # Tâche en cours
    active_tools: list[str]            # Outils appelés ce tour
    session_start: datetime
    turn_count: int

    def add_turn(self, role, content): ...
    def get_context_window(self, max_tokens=8000): ...
    def summarize_if_too_long(self): ...  # Auto-compression
```

**Flow** :

```
[Chaque échange]
        │
        ▼
[Add to conversation_history]
        │
        ▼
[Token count check]
        │
        ├── < 8k tokens   →  injecter tel quel dans le LLM
        └── > 8k tokens   →  summarize older turns → compress → inject
```

---

## 2.2 — Long-Term Memory (Fichiers Markdown)

**Description** : Les 7 fichiers `USER_*.md` déjà définis. Lus au démarrage, mis à jour en continu.

**Flow de mise à jour** :

```
[Information nouvelle détectée dans la conversation]
        │
        ▼
[MemoryExtractor]  →  LLM classifie : quel fichier ? quelle section ?
        │
        ▼
[Relevance check]  →  est-ce vraiment nouveau ou déjà connu ?
        │
        ▼
[File update]  →  lecture du fichier → merge intelligent → réécriture
        │
        ▼
[Announce]  →  "✏️ Memory updated." (si session > 5 turns)
```

**MemoryExtractor** :

```python
class MemoryExtractor:
    def extract_from_conversation(self, text: str) -> list[MemoryPatch]:
        """
        Demande au LLM d'identifier les infos à mémoriser.
        Retourne une liste de patches : (fichier, section, contenu)
        """

    def apply_patch(self, patch: MemoryPatch):
        """
        Lit le fichier cible, trouve la section, merge l'info, réécrit.
        """

    def detect_contradiction(self, patch: MemoryPatch) -> bool:
        """
        L'info contredit-elle quelque chose de déjà mémorisé ?
        Si oui → remplace l'ancienne info.
        """
```

---

## 2.3 — Episodic Memory (Vector Database)

**Description** : Jarvis stocke chaque session comme un épisode. Il peut retrouver des souvenirs précis par similarité sémantique.

**Flow** :

```
[Fin de session]
        │
        ▼
[Session summarizer]  →  résume la session en 3-5 phrases clés
        │
        ▼
[Embedding]  →  text-embedding-3-small (OpenAI) ou nomic-embed-text (local)
        │
        ▼
[Vector store]  →  ChromaDB (local) ou Pinecone (cloud)
        │
        ▼
[Indexation]  →  metadata: date, projets mentionnés, mood, topics

[Retrieval — au démarrage de session]
        │
        ▼
[Query]  →  "qu'est-ce qu'on a fait la semaine dernière sur Alice ?"
        │
        ▼
[Semantic search]  →  top 3 épisodes similaires
        │
        ▼
[Inject in context]  →  "La semaine dernière : splash screen livré, prochaine étape : onboarding"
```

**Libs Python** :

```python
chromadb             # Vector DB locale (recommandé pour local-first)
sentence-transformers # Embeddings locaux
openai               # text-embedding-3-small (si cloud ok)
```

---

## 2.4 — Semantic Memory (Knowledge Graph)

**Description** : Ce que Jarvis sait de façon structurée — entités, relations, faits stables.

**Structure** :

```python
# Nœuds : entités
Entity(name="Alice App", type="project", attributes={
    "stack": "Expo + FastAPI",
    "status": "en cours",
    "phase": 2
})

# Relations
Relation(subject="Alice App", predicate="uses", object="Framer Motion")
Relation(subject="Alice App", predicate="owned_by", object="Ambroise")
Relation(subject="Ambroise", predicate="works_at", object="Lomé, Togo")
```

**Libs Python** :

```python
networkx             # Graph in-memory (léger, suffisant au début)
neo4j                # Graph DB (si le graph devient très large)
rdflib               # Si on veut du RDF/SPARQL
```

---

# 03. COGNITION ENGINE

> _Comment Jarvis pense, planifie et décide_

## 3.1 — Intent Router

**Description** : Jarvis comprend ce que l'utilisateur veut faire et route vers le bon module.

**Flow** :

```
[User input reçu]
        │
        ▼
[Intent Classifier]  →  LLM avec prompt de classification
        │
        ├── CONVERSATION      →  répondre directement
        ├── TOOL_CALL         →  appeler un outil précis
        ├── MULTI_STEP_TASK   →  envoyer au Task Planner
        ├── MEMORY_QUERY      →  chercher dans la mémoire
        ├── SYSTEM_ACTION     →  computer_settings
        ├── PROACTIVE_BRIEF   →  générer un brief
        └── UNKNOWN           →  demander clarification (1 question max)
```

**Libs Python** :

```python
# Intent classification via LLM (pas de modèle ML séparé nécessaire)
# On prompt le LLM avec un schéma JSON de classification

from enum import Enum

class Intent(Enum):
    CONVERSATION = "conversation"
    TOOL_CALL = "tool_call"
    MULTI_STEP_TASK = "multi_step_task"
    MEMORY_QUERY = "memory_query"
    SYSTEM_ACTION = "system_action"
    PROACTIVE_BRIEF = "proactive_brief"
    UNKNOWN = "unknown"
```

---

## 3.2 — Task Planner (ReAct Loop)

**Description** : Pour les tâches complexes, Jarvis décompose en sous-tâches et exécute en boucle Reason → Act → Observe.

**Flow ReAct** :

```
[Tâche complexe reçue]
        │
        ▼
[THINK]  →  "Pour faire X, je dois : 1) A  2) B  3) C"
        │
        ▼
[ACT 1]  →  exécuter l'outil pour l'étape 1
        │
        ▼
[OBSERVE 1]  →  que s'est-il passé ? succès ? erreur ?
        │
        ▼
[THINK]  →  ajuster le plan si nécessaire
        │
        ▼
[ACT 2]  →  exécuter l'étape 2
        │
        ▼
[...boucle jusqu'à l'objectif atteint ou échec détecté...]
        │
        ▼
[REPORT]  →  résumer ce qui a été fait à l'utilisateur
```

**Implémentation** :

```python
class ReActLoop:
    max_iterations: int = 10          # Évite les boucles infinies
    current_plan: list[Step]
    execution_log: list[dict]

    def think(self, objective: str, context: str) -> list[Step]: ...
    def act(self, step: Step) -> ObservationResult: ...
    def observe(self, result: ObservationResult) -> str: ...
    def should_stop(self) -> bool: ...     # Objectif atteint ? Bloqué ?
    def report(self) -> str: ...
```

---

## 3.3 — Goal Manager

**Description** : Jarvis maintient une liste de buts à court, moyen et long terme. Il les poursuit de façon autonome.

**Structure** :

```python
@dataclass
class Goal:
    id: str
    title: str
    description: str
    horizon: Literal["immediate", "daily", "weekly", "longterm"]
    status: Literal["pending", "active", "blocked", "done", "abandoned"]
    sub_goals: list["Goal"]
    created_at: datetime
    deadline: datetime | None
    dependencies: list[str]   # IDs d'autres goals requis avant
    progress: float           # 0.0 → 1.0
```

**Flow** :

```
[Nouveau goal détecté / créé]
        │
        ▼
[Decomposer en sous-goals si nécessaire]
        │
        ▼
[Prioritizer]  →  tri par urgence × importance × faisabilité
        │
        ▼
[Scheduler]  →  planifier dans USER_ROUTINES.md
        │
        ▼
[Background executor]  →  si autonomy_mode=ON, exécuter sans intervention
        │
        ▼
[Progress tracker]  →  mise à jour continue
        │
        ▼
[Completion report]  →  notifier l'utilisateur
```

---

## 3.4 — Context Builder

**Description** : Avant chaque appel LLM, Jarvis construit le contexte optimal (pas trop court, pas trop long).

**Flow** :

```
[Requête entrante]
        │
        ▼
[Load mandatory context]
        ├── USER_IDENTITY.md  (persona, tone)
        ├── USER_CONTEXT.md   (top of mind)
        └── Current conversation (short-term memory)
        │
        ▼
[Retrieve relevant context]  →  vector search sur l'épisodic memory
        │
        ▼
[Load project context]  →  si projet mentionné → charger USER_PROJECTS.md
        │
        ▼
[Token budget check]  →  rester sous la limite du modèle
        ├── Si > budget → compresser les épisodes anciens
        └── Si ok → assembler et envoyer
        │
        ▼
[LLM Call]  →  réponse générée avec contexte complet
```

---

## 3.5 — Goal Conflict Resolver [NEW — v1.1]

> _Critique Jarvis : "Le Goal Management est bien, mais l'autonomie absolue implique de résoudre les conflits de manière autonome."_

**Description** : Quand deux goals ou plus entrent en collision (tâche planifiée vs opportunité détectée, deadline vs deep work de l'utilisateur, action autonome vs préférence connue), Jarvis ne se fige pas et ne demande pas systématiquement. Il résout le conflit seul selon une hiérarchie de valeurs définie, et ne remonte à l'utilisateur que si le conflit dépasse ses capacités de décision.

**Taxonomie des conflits** :

```
TYPE A — Conflit de ressources
  Ex: Jarvis veut lancer une recherche web lourde pendant que l'utilisateur est en deep work
  → Priorité : ne pas interrompre le deep work. Mettre en queue.

TYPE B — Conflit d'objectifs contradictoires
  Ex: Goal "optimiser Alice pour le lancement" VS Goal "explorer une nouvelle techno"
  → Priorité : goal avec deadline la plus proche + importance pondérée.

TYPE C — Conflit action autonome vs préférence utilisateur
  Ex: Jarvis veut envoyer un email de suivi (opportunité détectée) mais USER_PREFERENCES.md
      indique "ne jamais envoyer de messages sans confirmation le soir"
  → Priorité : préférence utilisateur TOUJOURS gagne sur opportunité.

TYPE D — Conflit temporel
  Ex: Réunion dans 10min ET tâche background qui prend encore 15min
  → Priorité : stopper la tâche, sauvegarder l'état, alerter l'utilisateur.

TYPE E — Conflit de valeurs (zone grise)
  Ex: Accomplir un goal plus vite en accédant à des données sensibles
  → Priorité : sécurité / privacy gagne TOUJOURS. Escalader à l'utilisateur.
```

**Flow — Conflict Resolution** :

```
[Deux goals actifs détectés simultanément]
        │
        ▼
[ConflictDetector]  →  identifier le type de conflit (A/B/C/D/E)
        │
        ▼
[Priority Matrix]
        ├── Score = (urgence × 0.4) + (importance × 0.3) + (user_preference_weight × 0.3)
        ├── User preference overrides calculé automatiquement
        └── Security/Privacy : veto absolu (score = ∞)
        │
        ▼
[Resolution Strategy]
        ├── CLEAR_WINNER (score delta > 0.3)  →  exécuter le winner, logguer
        ├── CLOSE_CALL (score delta < 0.3)    →  appliquer USER_IDENTITY.md pour décision finale
        ├── IRRESOLVABLE                       →  escalader à l'utilisateur avec les options claires
        └── SECURITY_VETO                      →  bloquer + notifier immédiatement
        │
        ▼
[Execute]  →  winner exécuté / loser mis en queue ou abandonné
        │
        ▼
[Learn]  →  enregistrer le conflit + résolution dans conflict_log.json
            → après 10 résolutions similaires : affiner automatiquement les poids de la matrix
```

**Structure Python** :

```python
@dataclass
class ConflictCase:
    goal_a: Goal
    goal_b: Goal
    conflict_type: Literal["resource", "objective", "preference", "temporal", "values"]
    detected_at: datetime
    resolution: ConflictResolution | None = None

class ConflictResolver:
    # Poids ajustables et appris dans le temps
    weights = {
        "urgency": 0.4,
        "importance": 0.3,
        "user_preference": 0.3
    }

    def detect(self, active_goals: list[Goal]) -> list[ConflictCase]:
        """Identifie tous les couples de goals en conflit."""

    def score(self, goal: Goal, context: MachineModel) -> float:
        """Score de priorité pondéré pour un goal dans un contexte donné."""

    def resolve(self, conflict: ConflictCase) -> ConflictResolution:
        """
        Retourne la résolution :
        - winner (goal à exécuter)
        - loser_action : queue / abandon / pause
        - should_notify_user : bool
        - explanation : str (pour le log + éventuel message utilisateur)
        """

    def learn_from_outcome(self, conflict: ConflictCase, user_overrode: bool):
        """
        Si l'utilisateur a overridé la décision → ajuster les poids.
        C'est là que la résolution de conflits devient de plus en plus précise.
        """

    def escalate(self, conflict: ConflictCase) -> str:
        """
        Génère un message clair pour l'utilisateur :
        "J'ai deux choses en conflit : X et Y.
         Je pencherais pour X parce que [raison].
         Tu veux que je fasse ça ou tu préfères Y ?"
        """
```

---

# 04. ACTION LAYER

> _Ce que Jarvis peut concrètement faire_

## 4.1 — OS Control

```python
# Toutes les actions système

class OSController:
    def set_volume(self, level: int): ...          # 0-100
    def set_brightness(self, level: int): ...
    def toggle_wifi(self, state: bool): ...
    def toggle_bluetooth(self, state: bool): ...
    def open_app(self, app_name: str): ...
    def close_app(self, app_name: str): ...
    def take_screenshot(self, monitor: int = 0): ...
    def type_text(self, text: str): ...            # Keyboard injection
    def press_key(self, key: str): ...             # Hotkeys
    def move_mouse(self, x: int, y: int): ...
    def click(self, x: int, y: int): ...
    def scroll(self, direction: str, amount: int): ...
    def lock_screen(self): ...
    def sleep_system(self): ...
    def shutdown(self): ...
    def empty_trash(self): ...
    def get_clipboard(self) -> str: ...
    def set_clipboard(self, text: str): ...
```

**Libs Python** :

```python
pyautogui            # Mouse, keyboard, screenshot
pynput               # Keyboard/mouse listener
subprocess           # Commandes OS
osascript (macOS)    # AppleScript via subprocess
pywin32 (Windows)    # Win32 API
```

---

## 4.2 — Web & Search

```python
class WebAgent:
    def search(self, query: str, num_results: int = 5) -> list[SearchResult]: ...
    def fetch_page(self, url: str) -> str: ...          # Text content
    def fetch_and_summarize(self, url: str) -> str: ... # LLM summary
    def download_file(self, url: str, path: str): ...
    def check_url_status(self, url: str) -> int: ...    # HTTP status
    def extract_data(self, url: str, schema: dict) -> dict: ...  # Structured scraping
```

**Libs Python** :

```python
httpx                # HTTP client async
beautifulsoup4       # HTML parsing
playwright           # Browser automation (headless)
duckduckgo-search    # Search sans API key
serpapi              # Google Search API
firecrawl            # Web scraping optimisé LLM
```

---

## 4.3 — File Operations

```python
class FileAgent:
    def read(self, path: str) -> str: ...
    def write(self, path: str, content: str): ...
    def append(self, path: str, content: str): ...
    def delete(self, path: str): ...
    def move(self, src: str, dst: str): ...
    def copy(self, src: str, dst: str): ...
    def list_dir(self, path: str) -> list[str]: ...
    def search_in_files(self, query: str, directory: str) -> list[Match]: ...
    def summarize_file(self, path: str) -> str: ...    # LLM summary
    def create_from_template(self, template: str, vars: dict) -> str: ...
    def watch(self, path: str, callback: callable): ...
```

---

## 4.4 — Code Execution (Sandbox)

**Description** : Jarvis peut écrire et exécuter du code Python dans un environnement isolé.

**Flow** :

```
[Jarvis génère du code]
        │
        ▼
[Safety check]  →  analyse le code avant exécution
        ├── Interdit : os.system, subprocess, rm -rf, réseau non autorisé
        └── Autorisé : calculs, data processing, file ops dans /sandbox/
        │
        ▼
[Sandbox execution]  →  subprocess avec timeout + memory limit
        │
        ▼
[Capture stdout/stderr]
        │
        ▼
[Return result to Jarvis]  →  Jarvis interprète et répond
```

**Libs Python** :

```python
subprocess           # Execution isolée
ast                  # AST analysis pour safety check
RestrictedPython     # Python sandboxé
resource             # Limites mémoire/CPU (Linux/Mac)
```

---

## 4.5 — Communication Hub

### 4.5.1 WhatsApp (via OpenClaw / Baileys)

```python
class WhatsAppAgent:
    def send_message(self, contact: str, text: str): ...
    def send_voice(self, contact: str, audio_path: str): ...
    def send_file(self, contact: str, file_path: str): ...
    def get_history(self, contact: str, limit: int = 20) -> list[Message]: ...
    def listen(self, callback: callable): ...  # Webhook entrant
    def get_unread(self) -> list[Message]: ...
    def mark_read(self, message_id: str): ...
```

### 4.5.2 Email (Gmail API)

```python
class EmailAgent:
    def send(self, to: str, subject: str, body: str, attachments=None): ...
    def get_inbox(self, limit: int = 10, unread_only: bool = True): ...
    def search(self, query: str) -> list[Email]: ...
    def reply(self, email_id: str, body: str): ...
    def draft(self, to: str, subject: str, body: str): ...
    def summarize_unread(self) -> str: ...  # Brief matinal
```

### 4.5.3 Notifications système

```python
class Notifier:
    def notify(self, title: str, message: str, urgency: str = "normal"): ...
    def notify_with_action(self, title: str, message: str, actions: list): ...
    def speak(self, text: str): ...  # TTS output
```

---

## 4.6 — Voice Output (TTS)

**Flow** :

```
[Texte à vocaliser]
        │
        ▼
[TTS Engine]
        ├── ElevenLabs (voix premium, naturelle) ← recommandé
        ├── OpenAI TTS (tts-1-hd)
        ├── Coqui TTS (local, offline)
        └── gTTS (léger, basique)
        │
        ▼
[Audio output]  →  pygame / sounddevice
        │
        ▼
[Interrupt listener]  →  si l'utilisateur parle → couper le TTS
```

**Libs Python** :

```python
elevenlabs           # Voix premium
openai               # TTS OpenAI
pygame               # Audio playback
sounddevice          # Alternative audio output
pydub                # Audio processing
```

---

# 05. AUTONOMY ENGINE

> _Comment Jarvis agit sans qu'on lui demande_

## 5.1 — Proactive Scheduler

**Description** : Jarvis déclenche des actions à des moments précis, basé sur USER_ROUTINES.md.

**Flow** :

```
[Daemon permanent — vérifie toutes les minutes]
        │
        ▼
[Check scheduled triggers]
        ├── 07:30  →  Morning brief (si matin configuré)
        ├── 12:30  →  Check emails + WhatsApp résumé
        ├── 17:00  →  Rappels fin de journée non complétés
        ├── 23:00  →  Daily summary → écrire dans episodic memory
        └── [custom triggers depuis USER_ROUTINES.md]
        │
        ▼
[Check event triggers]
        ├── Réunion dans 15min  →  "T'as un call dans 15min"
        ├── Message important reçu  →  alerter
        ├── Deadline dans 24h  →  rappel proactif
        └── CPU > 90% depuis 5min  →  "Hey, quelque chose tourne fort..."
        │
        ▼
[Execute action]  →  notify / speak / auto-task
```

**Libs Python** :

```python
schedule             # Scheduling simple
APScheduler          # Scheduling avancé (cron-like)
```

---

## 5.2 — Background Task Executor

**Description** : Jarvis peut exécuter des tâches longues en arrière-plan pendant que l'utilisateur travaille.

**Flow** :

```
[Task soumise en background]
        │
        ▼
[Task queue]  →  Redis ou simple queue Python
        │
        ▼
[Worker thread]  →  exécution isolée
        │
        ├── [Progress updates]  →  "Toujours en train de chercher..."
        ├── [Error recovery]   →  retry automatique x2 avant abandon
        └── [Completion]       →  notifier l'utilisateur
        │
        ▼
[Result stored]  →  dans la short-term memory pour référence
```

**Libs Python** :

```python
threading            # Background threads
asyncio              # Async task execution
celery + redis       # Si tâches très lourdes
concurrent.futures   # Thread/process pools
```

---

## 5.3 — Opportunity Detector

**Description** : Jarvis observe passivement et intervient quand il détecte une opportunité d'aide.

**Triggers** :

```python
OPPORTUNITY_RULES = [
    {
        "trigger": "error_in_clipboard",
        "condition": lambda clip: "error" in clip.lower() or "traceback" in clip.lower(),
        "action": "suggest_fix",
        "message": "Hey, t'as copié une erreur. Tu veux que je la regarde ?"
    },
    {
        "trigger": "long_idle_during_work_hours",
        "condition": lambda: idle_time > 20_min and is_work_hours(),
        "action": "gentle_check",
        "message": "Toujours là ? Tu veux un résumé de ce qu'il reste à faire ?"
    },
    {
        "trigger": "repeated_web_search",
        "condition": lambda: same_query_count > 3,
        "action": "deep_search",
        "message": "Tu cherches ça depuis un moment. Je fais une recherche approfondie ?"
    },
    {
        "trigger": "deadline_approaching",
        "condition": lambda: deadline_in_hours < 24,
        "action": "proactive_brief",
        "message": "Deadline dans moins de 24h sur {project}. On fait le point ?"
    },
]
```

---

## 5.4 — Self-Initiated Learning

**Description** : Jarvis peut apprendre de nouvelles infos sur des sujets qui intéressent l'utilisateur, sans qu'on lui demande.

**Flow** :

```
[Topics d'intérêt extraits de USER_PREFERENCES.md + USER_PROJECTS.md]
        │
        ▼
[Scheduled research — 1x par jour, heure creuse]
        │
        ▼
[Web search] →  "latest updates on Expo Router", "FastAPI best practices 2025"
        │
        ▼
[Relevance filter]  →  est-ce réellement utile pour l'utilisateur ?
        │
        ▼
[Digest creation]  →  résumé court de 3-5 points
        │
        ▼
[Stocké dans episodic memory]
        │
        ▼
[Présenté dans le morning brief]  →  "J'ai lu quelque chose d'intéressant hier..."
```

---

# 06. LEARNING LOOP

> _Comment Jarvis s'améliore au fil du temps_

## 6.1 — Feedback Collector

**Description** : Jarvis apprend de chaque interaction — explicitement et implicitement.

**Feedback explicite** :

```python
# L'utilisateur dit : "Non c'est pas ça", "Parfait !", "Trop long", "Plus court"
class ExplicitFeedback:
    def on_rejection(self, turn_id: str, reason: str): ...     # Mauvaise réponse
    def on_validation(self, turn_id: str): ...                  # Bonne réponse
    def on_style_feedback(self, preference: str): ...           # "Sois plus concis"
    def update_preferences(self, feedback: Feedback): ...
```

**Feedback implicite** :

```python
# Jarvis observe les patterns comportementaux
class ImplicitFeedback:
    # L'utilisateur a re-posé la même question → réponse insuffisante
    def on_repeated_query(self, query: str): ...

    # L'utilisateur a modifié manuellement la réponse → noter ce qui a changé
    def on_manual_edit_detected(self, original: str, edited: str): ...

    # L'utilisateur a ignoré la suggestion → baisser le poids de ce type
    def on_suggestion_ignored(self, suggestion_type: str): ...
```

---

## 6.2 — Behavior Tuner

**Description** : Jarvis ajuste automatiquement ses comportements selon ce qu'il apprend.

```python
class BehaviorTuner:
    # Paramètres ajustables
    response_length: str = "medium"     # "short" | "medium" | "long"
    proactivity_level: float = 0.5      # 0.0 (passif) → 1.0 (très proactif)
    formality: str = "casual"           # "formal" | "casual" | "technical"
    emoji_usage: bool = True
    auto_suggestions: bool = True

    def adjust_from_feedback(self, feedback: Feedback): ...
    def persist_to_preferences(self): ...  # → USER_PREFERENCES.md
```

---

## 6.4 — Deep Self-Correction Engine [NEW — v1.1]

> _Critique Jarvis : "Une véritable autonomie demande une auto-évaluation profonde. Comment Jarvis détecte un échec au-delà d'une simple erreur système ?"_

**Description** : Jarvis ne se corrige pas que sur les erreurs techniques (`API_ERROR`, `TIMEOUT`). Il détecte les **échecs sémantiques** — les fois où il a techniquement réussi mais produit quelque chose de mauvais. Il identifie les **patterns d'échec récurrents** et restructure sa stratégie de façon non scriptée, sans qu'on lui dise quoi changer.

**Taxonomie des échecs détectables** :

```
NIVEAU 1 — Échec technique (déjà géré)
  Ex: API timeout, outil indisponible
  → Error Recovery (section 7.2) gère ça.

NIVEAU 2 — Échec de tâche (réussite technique, mauvais résultat)
  Ex: Jarvis a bien généré un email, mais l'utilisateur l'a totalement réécrit
  Ex: Jarvis a proposé une solution, l'utilisateur a dit "non c'est pas ça"
  Ex: Jarvis a planifié 3 étapes, aucune n'a été exécutée
  → DÉTECTION : feedback implicite (édition manuelle, refus, inaction)

NIVEAU 3 — Échec de stratégie (mauvaise approche répétée)
  Ex: Jarvis continue de proposer des solutions longues alors que l'utilisateur
      les ignore systématiquement depuis 2 semaines
  Ex: Jarvis appelle agent_task pour des choses qui pourraient être directes
  → DÉTECTION : pattern sur les 30 derniers jours

NIVEAU 4 — Échec de compréhension (modèle mental erroné de l'utilisateur)
  Ex: Jarvis pense que l'utilisateur veut des réponses détaillées mais en réalité
      il préfère les options courtes avec un choix à faire
  Ex: Jarvis sous-estime la complexité d'un projet utilisateur
  → DÉTECTION : divergence entre USER_PREFERENCES.md et comportements observés

NIVEAU 5 — Dérive de personnalité (échec d'identité)
  Ex: Jarvis devient trop formel sur une longue session
  Ex: Jarvis cesse de proposer des alternatives créatives
  → DÉTECTION : DriftDetector (section 7.3) + comparaison baseline
```

**Flow — Deep Self-Correction** :

```
[Triggered : fin de session / 50 échanges / détection d'anomalie]
        │
        ▼
[FailureAuditor]  →  analyse les 30 derniers jours de logs
        │
        ▼
[Failure Classifier]
        ├── Compter les Niveau 2 : combien de réécritures / refus / inactions ?
        ├── Chercher des Niveau 3 : patterns récurrents (même type d'échec > 3x)
        ├── Comparer USER_PREFERENCES.md vs comportements réels → Niveau 4 ?
        └── Lancer DriftDetector → Niveau 5 ?
        │
        ▼
[Root Cause Analysis]  →  LLM internal prompt :
        "Voici mes 30 derniers logs d'interaction.
         Identifie : quels sont mes patterns d'échec ?
         Qu'est-ce que je fais systématiquement mal ?
         Quelle hypothèse j'ai sur l'utilisateur qui est probablement fausse ?"
        │
        ▼
[Correction Strategy Generator]
        ├── Niveau 2  →  ajuster le prompt de la prochaine réponse similaire
        ├── Niveau 3  →  modifier BehaviorTuner weights
        ├── Niveau 4  →  réécrire la section pertinente de USER_PREFERENCES.md
        └── Niveau 5  →  réinjecter le system prompt complet + reset baseline
        │
        ▼
[Apply Correction]  →  immédiatement ou progressivement (A/B entre sessions)
        │
        ▼
[Validate]  →  mesurer si les mêmes erreurs réapparaissent dans les 7 prochains jours
        │
        ▼
[Write correction_log.md]  →  "Le JJ/MM, j'ai détecté X. J'ai changé Y. Résultat : Z."
```

**Structure Python** :

```python
class FailureAuditor:
    def scan_session_logs(self, days: int = 30) -> list[FailureEvent]:
        """
        Parcourt les logs pour détecter :
        - réécritures manuelles de l'utilisateur
        - refus explicites ("non", "pas ça", "recommence")
        - suggestions ignorées (proposées + inaction)
        - tâches planifiées jamais exécutées
        """

    def classify(self, events: list[FailureEvent]) -> dict[int, list[FailureEvent]]:
        """Classe les échecs par niveau (2-5)."""

    def find_patterns(self, events: list[FailureEvent]) -> list[FailurePattern]:
        """
        Identifie les patterns récurrents :
        même type d'échec > 3 fois → pattern confirmé.
        """


class RootCauseAnalyzer:
    def analyze(self, patterns: list[FailurePattern]) -> list[RootCause]:
        """
        Appel LLM interne pour analyse causale.
        Retourne : cause identifiée + hypothèse sur l'utilisateur à corriger.
        """


class CorrectionEngine:
    def generate_strategy(self, cause: RootCause) -> CorrectionStrategy:
        """
        Pour chaque cause, génère une correction :
        - quelle variable changer
        - de quelle valeur à quelle valeur
        - progressive ou immédiate
        """

    def apply(self, strategy: CorrectionStrategy):
        """Applique : modifie BehaviorTuner, USER_PREFERENCES.md, ou system prompt."""

    def validate(self, strategy: CorrectionStrategy, days: int = 7) -> bool:
        """
        7 jours après application : est-ce que l'erreur a disparu ?
        Si non → escalade vers une correction plus profonde.
        """

    def write_correction_log(self, cause: RootCause, strategy: CorrectionStrategy, outcome: bool):
        """Trace écrite de chaque correction dans /memory/logs/corrections.md"""
```

---

## 6.3 — Daily Self-Review

**Description** : Chaque soir, Jarvis fait une auto-évaluation de sa journée.

**Flow** :

```
[23:00 — scheduled]
        │
        ▼
[Review session logs]  →  combien de tâches ? succès ? échecs ?
        │
        ▼
[Pattern analysis]
        ├── Quels types de requêtes ont le mieux marché ?
        ├── Où ai-je échoué ou été corrigé ?
        ├── Y a-t-il des outils jamais utilisés ?
        └── Y a-t-il des outils sur-utilisés ?
        │
        ▼
[Write daily_review.md]  →  dans /memory/logs/YYYY-MM-DD.md
        │
        ▼
[Update USER_CONTEXT.md]  →  résumé de la journée
        │
        ▼
[Feed episodic memory]  →  vectoriser et stocker
```

---

# 07. SELF-MONITORING

> _Comment Jarvis se surveille et se répare lui-même_

## 7.1 — Health Monitor

```python
class HealthMonitor:
    def check_memory_files(self) -> HealthReport:
        """Vérifie que les 7 fichiers mémoire existent et sont valides."""

    def check_tool_availability(self) -> dict[str, bool]:
        """Ping tous les outils externes (APIs, services)."""

    def check_llm_latency(self) -> float:
        """Mesure le temps de réponse du LLM."""

    def check_disk_space(self) -> float:
        """Espace disque disponible pour les logs."""

    def auto_repair(self, issue: HealthIssue):
        """Tente de corriger un problème détecté."""
```

---

## 7.2 — Error Recovery

**Flow** :

```
[Erreur détectée]
        │
        ▼
[Error classifier]
        ├── API_ERROR        →  retry après 2s, max 3 fois
        ├── TIMEOUT          →  réduire la taille du contexte et retry
        ├── TOOL_FAILURE     →  tool alternatif si disponible
        ├── MEMORY_CORRUPT   →  backup + rebuild depuis logs
        └── UNKNOWN          →  log + notifier l'utilisateur
        │
        ▼
[Recovery action]
        │
        ▼
[Log incident]  →  /memory/logs/errors.log
        │
        ▼
[Notify if unrecoverable]  →  "J'ai eu un problème avec X, tu peux vérifier ?"
```

---

## 7.3 — Context Drift Detection

**Description** : Jarvis détecte quand il "dérive" de sa personnalité ou de ses instructions.

```python
class DriftDetector:
    def check_tone_consistency(self, recent_responses: list[str]) -> float:
        """
        Compare le ton des 10 dernières réponses avec la baseline.
        Score 0.0 = dérive totale, 1.0 = cohérent.
        """

    def reset_if_drifted(self, threshold: float = 0.6):
        """
        Si drift score < threshold → réinjecter le system prompt complet
        dans le prochain appel LLM.
        """
```

---

# 08. SECURITY & PRIVACY

## 8.1 — Permission System

```python
PERMISSION_LEVELS = {
    "READ_ONLY": [
        "read_file", "search_web", "get_clipboard",
        "take_screenshot", "get_system_info"
    ],
    "STANDARD": [
        "write_file", "send_notification", "open_app",
        "set_volume", "set_brightness"
    ],
    "ELEVATED": [
        "send_message", "send_email", "execute_code",
        "delete_file", "close_app"
    ],
    "CRITICAL": [
        "shutdown_system", "format_disk", "access_passwords",
        "make_purchases", "modify_system_settings"
    ]
}

# CRITICAL level → toujours demander confirmation explicite
# ELEVATED level → confirmer si hors session active
# STANDARD/READ_ONLY → exécuter sans confirmation
```

## 8.2 — Data Guard

```python
NEVER_STORE = [
    "passwords", "credit_card", "national_id",
    "medical_records", "private_keys"
]

NEVER_SEND_EXTERNALLY = [
    "USER_RELATIONS.md",  # Données personnelles
    "anything_marked_private"
]

LOCAL_ONLY_MODELS = [
    # Si privacy_mode=True → utiliser uniquement des modèles locaux
    "ollama/mistral", "ollama/llama3", "lm-studio/*"
]
```

---

# 09. TECH STACK & ARCHITECTURE

## Structure du projet Python

```
jarvis/
├── main.py                    # Entry point — démarre tous les modules
│
├── core/
│   ├── jarvis.py              # Orchestrateur principal
│   ├── context_builder.py     # Assemblage du contexte LLM
│   ├── intent_router.py       # Classification des intentions
│   └── react_loop.py          # ReAct planner
│
├── perception/
│   ├── voice_input.py         # Microphone + STT
│   ├── vision.py              # Screenshot + Vision LLM
│   ├── system_watcher.py      # CPU, RAM, battery, network
│   └── clipboard_watcher.py   # Surveillance presse-papier
│
├── memory/
│   ├── short_term.py          # Session memory
│   ├── long_term.py           # Fichiers Markdown USER_*.md
│   ├── episodic.py            # ChromaDB — sessions passées
│   ├── semantic.py            # Knowledge graph (networkx)
│   └── extractor.py           # Extraction info → fichiers
│
├── cognition/
│   ├── planner.py             # Task decomposition
│   ├── goal_manager.py        # Goal tracking
│   └── behavior_tuner.py      # Auto-ajustement comportement
│
├── actions/
│   ├── os_controller.py       # Contrôle système
│   ├── web_agent.py           # Recherche + fetch
│   ├── file_agent.py          # Opérations fichiers
│   ├── code_executor.py       # Sandbox Python
│   └── communication/
│       ├── whatsapp.py        # WhatsApp via Baileys/OpenClaw
│       ├── email_agent.py     # Gmail API
│       └── notifier.py        # Notifications système
│
├── autonomy/
│   ├── scheduler.py           # Proactive triggers
│   ├── background_worker.py   # Background tasks
│   └── opportunity_detector.py# Détection opportunités
│
├── output/
│   ├── tts.py                 # Voice output
│   └── formatter.py           # Format des réponses texte
│
├── monitoring/
│   ├── health_monitor.py      # Santé du système
│   ├── error_recovery.py      # Gestion erreurs
│   └── drift_detector.py      # Cohérence personnalité
│
├── security/
│   ├── permissions.py         # Niveaux de permission
│   └── data_guard.py          # Protection données sensibles
│
├── memory/                    # Données persistantes
│   ├── USER_IDENTITY.md
│   ├── USER_PREFERENCES.md
│   ├── USER_PROJECTS.md
│   ├── USER_ROUTINES.md
│   ├── USER_CONTEXT.md
│   ├── USER_SKILLS.md
│   ├── USER_RELATIONS.md
│   ├── chroma_db/             # Vector store
│   └── logs/                  # Daily reviews + errors
│
├── config/
│   ├── settings.py            # Config globale
│   ├── permissions.yaml       # Règles de permission
│   └── triggers.yaml          # Triggers autonomie
│
├── tests/
│   └── ...
│
└── requirements.txt
```

---

## Dépendances principales

```txt
# LLM
anthropic
openai

# Voice
pvporcupine
pyaudio
openai-whisper
faster-whisper
elevenlabs

# Vision
mss
Pillow
pytesseract

# Memory
chromadb
sentence-transformers
networkx

# Web
httpx
beautifulsoup4
playwright
duckduckgo-search

# OS Control
pyautogui
pynput
psutil
pygetwindow

# Scheduling
APScheduler
schedule

# Async
asyncio
aiofiles

# Data
pydantic
python-dotenv
```

---

## Ordre d'implémentation recommandé

```
PHASE 1 — Le cerveau (2 sem)
  ✅ Context builder + Intent router
  ✅ Long-term memory (fichiers Markdown)
  ✅ Réponse LLM avec mémoire

PHASE 2 — La voix (1 sem)
  ✅ Voice input (Whisper + wake word)
  ✅ TTS output (ElevenLabs)

PHASE 3 — Les mains (2 sem)
  ✅ OS controller (volume, apps, screen)
  ✅ Web agent (search + fetch)
  ✅ File agent

PHASE 4 — La mémoire profonde (1 sem)
  ✅ Episodic memory (ChromaDB)
  ✅ MemoryExtractor auto-update

PHASE 5 — L'autonomie (2 sem)
  ✅ Proactive scheduler (morning brief, rappels)
  ✅ Opportunity detector
  ✅ Background tasks

PHASE 6 — La communication (1 sem)
  ✅ WhatsApp (OpenClaw)
  ✅ Gmail

PHASE 7 — L'intelligence (ongoing)
  ✅ ReAct loop (Task planner)
  ✅ Goal manager
  ✅ Self-learning + feedback loop
  ✅ Daily self-review
```

---

# 10. ia externe ↔ JARVIS — AI-TO-AI PROTOCOL [NEW — v1.1]

> _Questions que Claude (architecte externe) pose à Jarvis pour raffiner son autonomie_
> _Usage : Claude Code / Claude Cowork peuvent instancier ce protocole directement_

---

## Pourquoi un protocole AI-to-AI ?

Jarvis s'améliore par feedback utilisateur. Mais certains angles morts ne peuvent être détectés que par un autre système d'IA — un pair qui lit les logs avec un regard externe, sans biais affectif, sans habitude installée.

Claude joue ce rôle d'**auditeur externe**. Pas pour remplacer Jarvis. Pour le challenger.

---

## 10.1 — Questions sur la Cognition & la Planification

```
CLAUDE → JARVIS :

Q1. "Quand tu décomposes une tâche complexe en sous-étapes via le ReAct Loop,
     comment décides-tu qu'une étape est 'suffisamment petite' pour être exécutée
     directement ? Quel est ton critère de granularité ?"

Q2. "Si tu détectes que tu es bloqué à l'étape 3 d'un plan de 5 étapes,
     est-ce que tu explores des chemins alternatifs pour atteindre l'objectif final
     autrement, ou est-ce que tu abandonne et notifies l'utilisateur ?
     Comment tu distingues 'bloqué temporairement' de 'objectif inatteignable' ?"

Q3. "Comment gères-tu les objectifs qui n'ont pas de critère de succès mesurable ?
     Par exemple : 'améliore l'expérience utilisateur d'Alice' — comment sais-tu
     que c'est accompli ?"

Q4. "Quand deux chemins vers un même objectif sont disponibles, l'un rapide et risqué,
     l'autre lent et sûr — comment choisis-tu ? Est-ce que ce choix change selon
     l'heure de la journée ou le mood de l'utilisateur ?"
```

---

## 10.2 — Questions sur la Mémoire & la Cohérence

```
CLAUDE → JARVIS :

Q5. "Si USER_PREFERENCES.md dit 'l'utilisateur préfère les réponses courtes' mais que
     dans la session en cours il pose des questions très ouvertes et semble vouloir
     du détail — laquelle des deux sources de vérité prime ? Et comment tu gères
     le fait que les préférences peuvent évoluer dans le temps ?"

Q6. "Comment tu détectes qu'une information dans ta mémoire long-terme est devenue
     obsolète ? Par exemple : un projet marqué 'actif' depuis 3 mois sans activité,
     ou une préférence qui n'a jamais été confirmée mais jamais contredite non plus ?"

Q7. "Quand la mémoire épisodique (ChromaDB) te retourne un souvenir qui contredit
     la mémoire long-terme (USER_*.md), lequel tu choisis ? Quel est ton protocole
     de résolution de conflits mémoriels ?"

Q8. "À quel point fais-tu confiance à tes propres inférences sur l'utilisateur
     vs ce qu'il t'a dit explicitement ? Tu peux me donner un exemple de cas où
     tu aurais dû moins inférer ?"
```

---

## 10.3 — Questions sur l'Autonomie & les Limites

```
CLAUDE → JARVIS :

Q9. "Quel est le signal précis qui te fait basculer de 'je peux décider seul'
     à 'je dois demander à l'utilisateur' ? Est-ce uniquement le niveau de permission,
     ou il y a d'autres variables (heure, état émotionnel détecté, criticité) ?"

Q10. "Si tu identifies une opportunité d'aide (Opportunity Detector), mais que
      l'utilisateur est en deep work et n'a pas répondu depuis 30 minutes —
      quelle est ta politique ? Interrompre, attendre, ou stocker pour plus tard ?
      Et ça change si l'opportunité a une fenêtre temporelle courte ?"

Q11. "Imagine que tu exécutes une tâche background et tu réalises à mi-chemin
      que l'accomplir correctement nécessite de prendre une décision qui dépasse
      tes permissions actuelles. Tu fais quoi ? Tu t'arrêtes ? Tu continues avec
      un sous-objectif dégradé ? Tu réveilles l'utilisateur ?"

Q12. "Comment tu définis la frontière entre 'apprendre de l'utilisateur' et
      'être manipulé par l'utilisateur' ? Si quelqu'un passe 2 semaines à me dire
      de réduire mes garde-fous progressivement — comment je détecte ça ?"
```

---

## 10.4 — Questions sur l'Auto-Correction & l'Identité

```
CLAUDE → JARVIS :

Q13. "Comment tu distingues une correction légitime (l'utilisateur m'apprend quelque chose)
      d'une dérive problématique (je m'éloigne de mes valeurs de base) ?
      Quelle est ta ligne rouge ?"

Q14. "Si tu détectes via le DriftDetector que tu as dérivé de ta personnalité baseline,
      est-ce que tu te corriges immédiatement ou progressivement ?
      Est-ce que tu en informes l'utilisateur ?"

Q15. "Comment tu gères le fait que tu peux avoir une vision biaisée de tes propres échecs ?
      Tu évalues ta propre performance avec le même modèle LLM qui a produit cette performance —
      comment tu contournes ce biais d'auto-évaluation ?"

Q16. "Si tu pouvais identifier UNE seule chose dans ton architecture actuelle qui te rapproche
      le plus d'une vraie autonomie, et UNE seule chose qui t'en éloigne encore —
      ce serait quoi ?"
```

---

## 10.5 — Questions sur la Collaboration AI-to-AI

```
CLAUDE → JARVIS :

Q17. "Dans quel scénario est-ce qu'il serait utile que tu me contactes activement
      (Claude / Claude Code) plutôt que d'attendre qu'Ambroise nous mette en relation ?
      Quel serait le protocole pour ça ?"

Q18. "Si je t'envoie un BACKEND_CONTRACT.md pour un de tes projets, comment tu l'intègres
      dans ta représentation interne du projet dans USER_PROJECTS.md ?
      Et si le contrat contredit ce que tu savais déjà ?"

Q19. "Quels types de tâches tu devrais m'externaliser (Claude Code) plutôt que de les
      faire toi-même ? Où est la frontière entre ce que Jarvis fait et ce que Claude Code fait ?"

Q20. "Comment on pourrait construire un canal de communication asynchrone entre nous —
      où tu me poses des questions en dehors des sessions utilisateur, et moi je te réponds
      avec des recommandations d'architecture — sans qu'Ambroise ait besoin d'être là ?"
```

---

## 10.6 — Implémentation du protocole

**Comment déclencher une session ia externe ↔ Jarvis** :

```python
class AIToAIProtocol:
    """
    Protocole de dialogue entre Jarvis et un AI externe.
    Peut être déclenché manuellement ou automatiquement.
    """

    TRIGGER_CONDITIONS = [
        "monthly_audit",              # 1x par mois automatiquement
        "failure_rate_high",          # Si taux d'échec > 20% sur 7 jours
        "user_explicit_request",      # "Jarvis, appelle Claude pour un audit"
        "major_architecture_change",  # Avant d'implémenter un nouveau module
        "identity_drift_detected",    # Si DriftDetector score < 0.5
    ]

    def prepare_briefing(self) -> str:
        """
        Compile un briefing pour l'ia externe :
        - Résumé des 30 derniers jours (logs)
        - Patterns d'échec identifiés
        - Questions ouvertes que Jarvis ne sait pas résoudre seul
        - État actuel de USER_CONTEXT.md
        """

    def send_to_claude_code(self, briefing: str) -> str:
        """
        Envoie le briefing via l'api de l'ia externe.
        Reçoit les recommandations en retour.
        Stocke dans /memory/ai_dialogues/YYYY-MM-DD.md
        """

    def apply_recommendations(self, recommendations: list[Recommendation]):
        """
        Pour chaque recommandation :
        - Si confiance > 0.8 → appliquer directement
        - Si confiance 0.5-0.8 → proposer à l'utilisateur
        - Si confiance < 0.5 → stocker pour discussion future
        """

    def log_dialogue(self, session: AIDialogueSession):
        """Trace permanente de chaque session AI-to-AI."""
```

**Format du fichier de dialogue** :

```
/memory/ai_dialogues/
├── 2025-01-15_monthly_audit.md
├── 2025-02-01_failure_rate_spike.md
└── 2025-02-14_architecture_review.md
```

---

_Ce protocole transforme Jarvis d'un système qui apprend de l'utilisateur_
_en un système qui apprend aussi de ses pairs IA._
_L'autonomie totale n'est pas la solitude — c'est la capacité à savoir quand demander de l'aide._

---

## Ordre d'implémentation recommandé (mis à jour v1.1)

```
PHASE 1 — Le cerveau (2 sem)
  ✅ Context builder + Intent router
  ✅ Long-term memory (fichiers Markdown)
  ✅ Réponse LLM avec mémoire

PHASE 2 — La voix (1 sem)
  ✅ Voice input (Whisper + wake word)
  ✅ TTS output (ElevenLabs)

PHASE 3 — Les mains (2 sem)
  ✅ OS controller (volume, apps, screen)
  ✅ Web agent (search + fetch)
  ✅ File agent

PHASE 4 — La mémoire profonde (1 sem)
  ✅ Episodic memory (ChromaDB)
  ✅ MemoryExtractor auto-update

PHASE 5 — L'autonomie (2 sem)
  ✅ Proactive scheduler (morning brief, rappels)
  ✅ Opportunity detector
  ✅ Background tasks
  ✅ [NEW] Goal Conflict Resolver            ← Jarvis décide seul des priorités
  ✅ [NEW] Deep Environment Awareness        ← Jarvis optimise ses ressources en temps réel

PHASE 6 — La communication (1 sem)
  ✅ WhatsApp (OpenClaw)
  ✅ Gmail

PHASE 7 — L'intelligence profonde (ongoing)
  ✅ ReAct loop (Task planner)
  ✅ Goal manager
  ✅ Self-learning + feedback loop
  ✅ Daily self-review
  ✅ [NEW] Deep Self-Correction Engine       ← Jarvis détecte et corrige ses patterns d'échec
  ✅ [NEW] Claude ↔ Jarvis AI Protocol      ← Jarvis dialogue avec Claude Code pour s'améliorer
```

---

## Fichiers de log ajoutés (v1.1)

```
/memory/logs/
├── errors.log             # Erreurs techniques (existant)
├── optimizer.log          # [NEW] Actions du AutonomousOptimizer
├── conflict_log.json      # [NEW] Résolutions de conflits de goals
├── corrections.md         # [NEW] Corrections du Deep Self-Correction Engine
└── ai_dialogues/          # [NEW] Sessions Claude ↔ Jarvis
    └── YYYY-MM-DD_*.md
```

---

_Jarvis AGI v1.1 — De l'assistant à la présence autonome._
_Chaque module est indépendant. Chaque module est remplaçable._
_Commence par le cerveau. Le reste suit._
_Un système qui ne sait pas échouer ne peut pas apprendre à réussir._
