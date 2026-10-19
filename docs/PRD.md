# PRD — JARVIS : Product Requirements Document

| | |
|---|---|
| **Document** | `PRD.md` (1/9 du lot documentaire de refonte) |
| **Dépôt / branche / commit audité** | `ametoessoambroise/jarvis` · `main` · `2dbb971` (3 commits, arbre de travail propre au moment de l'audit) |
| **Date de l'audit** | 2026-10-18 |
| **Statut** | Proposition CTO soumise à revue — aucune implémentation n'a été réalisée |
| **Documents liés** | `TRD.md` (architecture), `APP_FLOW.md` (flux), `DEVELOPMENT_PHASES.md` (plan), `RISKS.md`, `DECISIONS.md`, `BACKEND_CONTRACT.md`, `BACKEND_SCHEMA.md`, `DESIGN_SYSTEM.md` |

> **Règle de lecture.** L'état « actuel » décrit dans ce document provient de la **lecture statique du code** du commit `2dbb971`. Rien n'a été exécuté : ni l'application, ni Gemini Live, ni Windows, ni les actions. Un statut « implémenté » signifie « le code existe et son chemin d'appel est câblé », jamais « testé et fiable ». Les anciens documents (`implementation.md`, `phases.md`, `readme.md`, `NEED.md`) sont des références **historiques**, pas des preuves d'implémentation.

---

## 1. Vision, problème et utilisateurs

### 1.1 Vision

JARVIS est un **agent IA personnel pour ordinateur** : il dialogue naturellement (voix ou texte), comprend une demande, planifie un objectif, utilise des outils, interagit avec l'environnement informatique et **vérifie le résultat réel** de ses actions — dans les limites et permissions que l'utilisateur lui accorde.

Ce n'est pas un chatbot vocal. La cible est un assistant capable de mener des tâches complètes, mais **l'autonomie n'est jamais présentée comme acquise** : elle est un objectif progressif, mesurable et borné (voir §7 et `DECISIONS.md` ADR-007).

### 1.2 Problème utilisateur

| Problème | Conséquence aujourd'hui (constaté dans le code) |
|---|---|
| Les assistants vocaux grand public ne contrôlent pas réellement l'ordinateur | JARVIS le fait (26 outils déclarés) mais sans garde-fous homogènes |
| Un agent qui agit sur la machine doit être contrôlable | Aucune confirmation n'est branchée (`confirm_critical_actions` n'est lu nulle part ; `ScreenOverlay.confirm_action` n'est jamais appelée) |
| L'utilisateur veut un assistant qui le connaît | Mémoire JSON fonctionnelle mais fragile (race, écrasement de sauvegarde, plafond de 8 000 caractères) |
| L'utilisateur veut des tâches multiétapes fiables | Deux mécanismes concurrents, dont un (`core/autonomy_manager.py`) purement simulé |
| L'utilisateur doit pouvoir faire confiance au dépôt | Une clé API est versionnée en clair ; aucun test automatisé |

### 1.3 Utilisateurs cibles

| Persona | Besoin | Version cible |
|---|---|---|
| **P-1 Propriétaire-développeur** (Ambroise, seul utilisateur aujourd'hui) | Un agent personnel fiable sur son PC Windows, évolutif, refactorisable par un agent codeur | V1 |
| **P-2 Utilisateur technique avancé** (clone le dépôt, fournit sa clé Gemini) | Installation documentée, configuration claire, erreurs compréhensibles | V1 |
| **P-3 Utilisateur sensible à la confidentialité** | Mode local/cloud choisi explicitement, pas d'envoi implicite de données personnelles | V1.5 |
| **P-4 Contributeur** | Tests, contrats, structure compréhensible | V1 / V1.5 |

Hors cible explicite : utilisateur final non technique (installateur grand public), usage multi-utilisateur, usage en entreprise.

---

## 2. Principes de produit (hérités du CTO, non négociables)

1. **Continuité > réécriture totale.** On préserve les fonctionnalités utiles.
2. **Modularité utile, pas cérémonielle.** Une abstraction doit résoudre un problème réel observé.
3. **L'autonomie est un objectif central**, accompagné de limites vérifiables.
4. **La sécurité accompagne l'autonomie.** Plus de capacité d'action ≠ liberté illimitée.
5. **Local et cloud coexistent** (V1.5).
6. **Windows d'abord**, frontières permettant d'autres OS plus tard.
7. **Mémoire exploitable et interrogeable** : RAG local progressif en V1.5.
8. **Aucune fonctionnalité fictive** : la documentation (et l'interface) reflète la réalité du code.

---

## 3. Application telle qu'elle existe (commit `2dbb971`)

### 3.1 Vue d'ensemble

- **Langage / UI** : Python (3.11+ requis par `asyncio.TaskGroup` ; le README indique 3.11/3.12) ; interface **PyQt6** (HUD sombre) ; un overlay Tkinter coexiste (`ui/screen_overlay.py`).
- **Volumétrie** : 75 fichiers suivis ; 59 fichiers Python, ≈ 16 900 lignes (`actions/` ≈ 10 300, `core/` ≈ 2 850, `ui/` ≈ 1 900, `agent/` ≈ 1 200, `memory/` ≈ 480, `logs/` ≈ 105).
- **Point d'entrée** : `main.py` crée `JarvisUI("face.png")` (le fichier `face.png` n'est pas dans le dépôt ; le HUD dégrade proprement vers « pas de visage »), attend la clé (`ui.wait_for_api_key()`), puis lance `JarvisLive.run()` dans un thread daemon avec sa propre boucle `asyncio` ; la boucle Qt tourne dans le thread principal.
- **Moteur IA actuel** : **Gemini Live** (`models/gemini-2.5-flash-native-audio-latest`, SDK `google-genai`, `api_version="v1alpha"`), audio 16 kHz entrant / 24 kHz sortant, voix « Charon », transcriptions entrante et sortante activées, 26 outils déclarés.
- **Second SDK Gemini** : `google-generativeai` (hérité) est utilisé par le planificateur, l'exécuteur, le gestionnaire d'erreurs, `code_helper`, `dev_agent`, `desktop.py` (modèles `gemini-2.5-flash` / `-flash-lite` / `2.0-flash`).
- **Mémoire** : `memory/long_term.json` (9 catégories) + 7 fichiers Markdown régénérés (`USER_*.md`), tous ignorés par Git.
- **Tests** : aucun test automatisé. Seul `test_live.py` existe : script de connexion **réelle** à Gemini.

### 3.2 Légende des statuts

| Statut | Signification |
|---|---|
| ✅ **Implémenté** | Code présent et branché dans un chemin d'appel réel (vérifié statiquement) |
| 🟡 **Partiel** | Fonctionne dans un périmètre réduit, ou avec défaut constaté |
| 🧪 **Expérimental / simulé** | Code présent mais données ou agents fictifs |
| 🔴 **Non branché / cassé** | Code présent mais jamais appelé, ou incohérence empêchant l'usage |
| ⏳ **Prévu** | N'existe pas dans le dépôt |

### 3.3 Capacités du cœur (hors outils)

| Capacité | Fichiers | Statut | Constats vérifiés |
|---|---|---|---|
| Conversation vocale temps réel (Gemini Live) | `core/jarvis_live.py`, `core/utils.py` | ✅ | 6 tâches dans un `TaskGroup` ; reconnexion jusqu'à 5 tentatives, erreurs d'authentification traitées comme fatales ; **pas de `session_resumption`** dans `_build_config` (présent seulement dans `test_live.py`) |
| Entrée texte | `ui/interface.py` → `JarvisLive._on_text_command` | 🟡 | Ignorée **silencieusement** si aucune session n'est ouverte |
| Appel d'outils par le modèle | `core/tools.py`, `JarvisLive._execute_tool` | ✅ | 26 outils ; dispatch par chaîne `if/elif` ; résultat par défaut `"Done."` même sans preuve de réussite |
| Mémoire persistante | `memory/memory_manager.py` | 🟡 | Voir §3.5 ; fonctionne, avec défauts de concurrence et de récupération |
| Notifications système → modèle | `core/notification_manager.py`, `JarvisLive._poll_notifications_loop` | ✅ (Windows/WinRT) | Contenu des notifications injecté tel quel comme tour utilisateur avec consigne de répondre via `send_message` |
| Partage d'écran | `core/screen_share_worker.py`, `actions/ui_inspector.py`, `ui/tray_indicator.py` | ✅ (Windows) | Image 640×360 JPEG q50 si changement, filtre de confidentialité ; **envoi de contexte UI avec `turn_complete=True` à chaque cycle** |
| Filtre de confidentialité | `core/privacy_guard.py`, `config/app_profiles.json` | 🟡 | Appliqué **uniquement** au partage d'écran ; ni `hotkey`, ni `screen_process`, ni `interact_ui` |
| Raccourci « regarde ici » (Ctrl+Shift+J) | `core/hotkey_listener.py` | 🟡 | Démarré à chaque reconnexion → enregistrements multiples ; sans filtre de confidentialité |
| Conscience du contexte / suggestions | `core/context_engine.py` | 🔴 | Moteur complet, mais la boucle `_context_awareness_loop` est **commentée** (`tg.create_task` désactivé) |
| Vérification d'action | `core/action_verifier.py` | 🟡 | Compare des empreintes d'écran : prouve « l'écran a changé », pas « l'action a réussi » ; sans `fallback_fn` il n'y a aucun retry |
| Journal d'actions | `logs/action_logger.py` | 🟡 | N'enregistre que `interact_ui` ; consigne le **texte tapé** ; `log_autonomy` jamais appelée |
| File de tâches agent | `agent/task_queue.py` | 🟡 | Voir §3.4 |
| Planificateur / exécuteur / gestion d'erreurs | `agent/planner.py`, `executor.py`, `error_handler.py` | 🟡 | Plan ≤ 5 étapes, 15 outils connus du planificateur, 16 branches dans `_call_tool` ; voir §3.4 |
| « Autonomie » | `core/autonomy_manager.py`, `actions/manage_autonomy.py` | 🧪 / 🔴 | **Aucun agent enregistré, aucune idée soumise** par le code applicatif ; les deux agents fournis sont des simulations ; le drapeau `enabled` n'est lu que dans du code mort ; `logging.basicConfig` appelé à l'import |
| Mode `--watch` (redémarrage à chaud) | `core/file_watcher.py`, `main.py` | ✅ (dev) | `os.execv` sur modification de `.py` |
| Configuration / clé API | `core/utils.py`, `ui/interface.py`, `config/__init__.py`, `memory/config_manager.py` | 🔴 | **Trois chemins différents** (voir §4) ; `memory/config_manager.py` n'est importé nulle part |

### 3.4 Détail agent / tâches (constats)

- `TaskQueue` marque une tâche **`COMPLETED` même quand l'exécuteur retourne un message d'abandon ou d'échec** (il retourne une chaîne au lieu de lever) ; une tâche annulée avant exécution reste dans `_queue` ; aucun état n'est persisté.
- `analyze_error(..., max_attempts=2)` force `REPLAN` dès la 2ᵉ tentative : la boucle d'`AgentExecutor` prévoit 3 tentatives, **la 3ᵉ n'est jamais atteinte**.
- La décision `SKIP` marque l'étape comme réussie ; le résumé final annonce « All done » sans distinguer.
- La règle du planificateur « ne jamais référencer les résultats précédents » coexiste avec `_inject_context` (qui injecte les résultats dans `file_controller` en `write`/`create_file`, avec traduction automatique par LLM) : le contrat de dépendance entre étapes est **implicite et incohérent**.
- Le chemin « auto-fix » (`generate_fix`) produit un pas `code_helper` avec un paramètre `code` que l'action `run` **ignore** (elle exige `file_path`) : elle renvoie une chaîne d'erreur **sans lever**, l'étape est donc comptée comme réussie.
- Deux dispatchers divergents : `JarvisLive._execute_tool` (26 outils) et `agent/executor._call_tool` (16 branches dont `generated_code`).

### 3.5 Détail mémoire (constats)

- Catégories : `identity, preferences, projects, routines, context, skills, relationships, wishes, notes` ; entrée = `{"value": str ≤ 380 car., "updated": "YYYY-MM-DD"}` ; plafond global 8 000 caractères (suppression des plus anciennes, signalée par un simple `print` console (invisible pour l'utilisateur)) ; injection au prompt limitée à 2 000 caractères.
- `update_memory` fait lecture → modification → écriture avec deux acquisitions de verrou distinctes : **course** possible entre appels concurrents.
- Si `long_term.json` est illisible, `load_memory()` renvoie une mémoire vide ; le prochain `save_memory` copie le fichier corrompu **par-dessus** `long_term.json.bak` : perte de la dernière bonne sauvegarde.
- L'outil `save_memory` du modèle n'**valide pas** la catégorie ; le contenu mémorisé est ré-injecté dans le prompt système au démarrage suivant (vecteur de persistance d'injection de prompt).
- Les catégories `wishes` et `notes` ne sont pas exportées en Markdown.

### 3.6 Les 26 outils déclarés (`core/tools.py`) — état

Nombre vérifié par analyse syntaxique de `TOOL_DECLARATIONS` : **26** ; chacun possède une branche dans `_execute_tool`.

| # | Outil | Module | Statut | Constats clés |
|---|---|---|---|---|
| 1 | `open_app` | `actions/open_app.py` | 🟡 | `subprocess.Popen(..., shell=True)` avec le nom fourni par le modèle (injection possible) |
| 2 | `web_search` | `actions/web_search.py` | ✅ | `ddgs` / `duckduckgo_search` ; modes `search`/`compare` |
| 3 | `weather_report` | `actions/weather_report.py` | 🟡 | S'appuie sur une recherche Google (mécanisme non approfondi) |
| 4 | `send_message` | `actions/send_message.py`, `send_message_utils.py` | 🟡 | Automatisation GUI (PyAutoGUI), WhatsApp en priorité ; **aucune confirmation** ; temporisations fixes |
| 5 | `get_context` | `actions/get_context.py` | 🟡 | Capture de l'historique de conversation par GUI (sélection/copie) |
| 6 | `reminder` | `actions/reminder.py` | ✅ (Windows) | Planificateur de tâches Windows (`schtasks` + XML) ; `win10toast` ; variantes macOS/Linux non vérifiées |
| 7 | `youtube_video` | `actions/youtube_video.py` | ✅ | play / summarize / trending ; `youtube-transcript-api` |
| 8 | `screen_process` | `actions/screen_processor.py` | 🟡 | Ouvre une **seconde** session Gemini Live (`…native-audio-preview-12-2025`) dans un thread daemon ; vision écran/caméra |
| 9 | `computer_settings` | `actions/computer_settings.py` | ✅ (Windows) | `pycaw`, `ctypes`, `winreg`, `subprocess` ; variantes Linux/macOS présentes |
| 10 | `manage_autonomy` | `actions/manage_autonomy.py` | 🧪 | Le **modèle** peut activer/désactiver l'autonomie ; sans effet réel (voir §3.3) |
| 11 | `system_optimizer` | `actions/system_optimizer.py` | 🟡 | `kill_process` (terminate puis kill) avec `dry_run` optionnel ; « undo » non implémenté |
| 12 | `iot_control` | `actions/iot_control.py` | 🧪 | **Simulation** : dictionnaire en mémoire de 3 appareils fictifs |
| 13 | `browser_control` | `actions/browser_control.py`, `browser_inspector.py` | 🟡 | Playwright, `launch_persistent_context` sur le **profil réel** du navigateur ; inspection via CDP :9222 |
| 14 | `file_controller` | `actions/file_controller.py` | ✅ | Racine autorisée = tout `~` ; suppression via corbeille (`send2trash`) ; dossiers utilisateur protégés |
| 15 | `desktop_control` | `actions/desktop.py` | 🟡 | Action `task` : code généré par LLM exécuté par **`exec` dans le processus** avec un « sandbox » de `__builtins__` |
| 16 | `code_helper` | `actions/code_helper.py` | 🟡 | write/edit/explain/run/build/optimize/screen_debug ; filtre AST **seulement** pour `.py` en `run` ; `.js/.sh/.ps1/…` exécutés sans filtre |
| 17 | `dev_agent` | `actions/dev_agent.py` | 🟡 | Génère des projets dans `~/Desktop/JarvisProjects`, `pip install` des dépendances produites par le LLM sans liste blanche (liste blanche seulement pour l'auto-install) |
| 18 | `agent_task` | `agent/*` | 🟡 | Voir §3.4 |
| 19 | `computer_control` | `actions/computer_control.py` | ✅ | type/click/hotkey/press/scroll/screenshot/screen_find/screen_click… |
| 20 | `game_updater` | `actions/game_updater.py` | 🟡 | Steam/Epic ; `winreg`, `pygetwindow`, `pywinauto` (très dépendant de Windows) ; 1 047 lignes, la plus longue action |
| 21 | `flight_finder` | `actions/flight_finder.py` | 🟡 | Passe par Google Flights (navigateur) |
| 22 | `shutdown_jarvis` | `core/jarvis_live.py` | 🟡 | `os._exit(0)` après 1 s : aucune fermeture propre |
| 23 | `file_processor` | `actions/file_processor.py` | 🟡 | PDF/DOCX/XLSX/CSV/PPTX… ; dépendances optionnelles **absentes de `requirements.txt`** |
| 24 | `save_memory` | `core/jarvis_live.py` | 🟡 | Voir §3.5 ; le prompt système parle de `memory_write` (nom inexistant) |
| 25 | `toggle_screen_share` | `core/jarvis_live.py` | ✅ | Active le worker et l'icône de zone de notification |
| 26 | `interact_ui` | `core/jarvis_live.py` | 🟡 | Clic/saisie par coordonnées avec aperçu overlay et `ActionVerifier` ; journalise le texte saisi |

### 3.7 Écarts entre promesses et réalité

| Source | Affirmation | Réalité vérifiée |
|---|---|---|
| `readme.md` | « Cross-platform : Windows, macOS, Linux » | Le code est massivement Windows-dépendant (≥ 20 imports/usages Windows, 57 branchements `platform`/`os.name`) ; la V1 supporte **Windows 10/11 uniquement** |
| `readme.md` | « Licensed under CC BY-NC 4.0 » | Le fichier `LICENSE` est **Apache-2.0** — contradiction à arbitrer par le propriétaire (voir §13) |
| `readme.md` | « Engineered for total autonomy » | L'autonomie n'existe pas encore (voir §3.3) |
| `readme.md` | « execute terminal commands » | Pas d'outil de terminal générique ; exécution de code via `code_helper`/`dev_agent`/`desktop_control` |
| `implementation.md` / `phases.md` | Architecture AGI en 9 couches (STT, wake word, base vectorielle, graphe de connaissances, Gmail, OpenClaw/Baileys…) | **Aucun** de ces composants n'existe dans le dépôt |
| `core/prompt.txt` | Outil `memory_write`, commandes « memory status », fichiers `USER_*.md` lisibles | L'outil s'appelle `save_memory` ; aucun outil de lecture des `USER_*.md` |
| UI footer | « FatihMakes Industries · MARK XXXIX » | Attribution héritée d'une base amont ; à clarifier vis-à-vis de la licence (voir §13) |

---

## 4. Constat bloquant : configuration et clé API

| Composant | Chemin lu/écrit pour la clé |
|---|---|
| `ui/interface.py` (dialogue de configuration, `_check_config`) | `ui/config/api_keys.json` (car `BASE_DIR` = dossier `ui/`) — **écrit en clair, avec `os_system`** |
| `core/utils._get_api_key()` (planificateur, exécuteur, Live…) | `GEMINI_API_KEY` puis `<racine>/config/api_keys.json` |
| `actions/*` (reminder, get_context, send_message, computer_control, screen_processor) et `config/__init__.py` | `<racine>/config/api_keys.json` (pour `os_system`) |
| `.gitignore` | ignore `config/api_keys.json` mais **pas** `ui/config/api_keys.json` |

Conséquences :
1. `ui/config/api_keys.json` est **versionné** (présent dans les 2 commits ; valeur non vide) → **clé API exposée**, désormais dans un dépôt public.
2. Sur un clone neuf, le dialogue de configuration écrit un fichier que le moteur ne lit pas → `RuntimeError: Gemini API key not found` sauf si `GEMINI_API_KEY` est défini.
3. `config/__init__.get_config()` plante si `config/api_keys.json` est absent (appelé par `flight_finder`, `game_updater`, `youtube_video`).

Cette situation fonde la phase **P0** (remédiation) puis **P1** (configuration unifiée) — voir `DEVELOPMENT_PHASES.md`.

---

## 5. Matrice des versions (référence unique pour les 9 documents)

| Domaine | Remédiation immédiate (R) | **V1** — stabilisation | **V1.5** — nouvelle architecture | **V2** — extension |
|---|---|---|---|---|
| Secrets | Révoquer/renouveler la clé, retirer le fichier du suivi Git, corriger `.gitignore` (P0) | `.env` + `config/settings.json` non secret, chemin unique (P1) | `secret_store` abstrait, adaptateur Windows Credential Manager facultatif (P13) | — |
| Outils | Retirer `shell=True` pilotés par le modèle, désactiver `exec` in-process (P7) | Registre unique, dispatcher, contrats d'outils préservés (P3) | Contrat d'action complet, risque/permissions par action (P14) | — |
| Orchestration | — | Fiabiliser `task_queue`/`executor` existants (P5) | **Un seul moteur** de tâches + autonomie à 4 niveaux (P15) | Autonomie étendue |
| Fournisseurs IA | — | Gemini uniquement ; adaptateur interne minimal si utile à la testabilité (P4) | Registre, capacités, routeur ; texte, voix temps réel, STT, TTS, embeddings (P10–P12) | Modèles/fournisseurs supplémentaires |
| Mémoire | — | Stabiliser JSON actuel, tests (P6) | Service mémoire SQLite + FTS5, vectoriel facultatif, RAG traçable (P17–P18) | Mémoire plus riche |
| Permissions | Confirmations minimales sur `send_message` & destructif **si nécessaire** (P7) | — | `permission_manager` + `confirmation_policy` (P13) | — |
| Plateformes | — | Windows seul ; dépendances documentées (P9) | Adaptateurs `platform/windows/` (P14) | Autres OS testés |
| UI | — | Tokens de design, dialogues, correctifs (P8) | Providers, permissions, progression, autonomie (P19) | Client web / séparation client-moteur |
| Tests | — | Suite offline + fakes (P2…P9) | Contrats providers, intégration opt-in, régression migration | — |

---

## 6. Périmètre V1 — Refonte et stabilisation

### 6.1 Fonctionnalités indispensables (MUST)

| ID | Exigence | Phase | Critère d'acceptation mesurable |
|---|---|---|---|
| V1-SEC-01 | Aucun secret ni donnée personnelle versionné ; clé exposée révoquée | P0, P1 | `git ls-files` ne contient aucun fichier `api_keys.json`, `.env`, `memory/long_term.json` ; un scan de secrets sur l'arbre de travail est vide ; la clé historique est invalide côté fournisseur (confirmation du propriétaire) |
| V1-CFG-01 | Un seul chemin de chargement de configuration, priorité explicite : variable d'environnement > `.env` utilisateur > `.env` racine (dev) > erreur explicite | P1 | Test unitaire de la table de priorité ; démarrage sans clé → message actionnable, pas de stacktrace |
| V1-CFG-02 | Les paramètres non secrets (`os_system`, notifications, profils) restent en JSON ; la clé n'est plus écrite en JSON | P1 | Test : `save_settings()` n'écrit jamais de clé ; dialogue de configuration écrit dans le `.env` sans effacer les autres clés |
| V1-TST-01 | Suite de tests unitaires **sans réseau ni vraie clé** : mémoire, contrats d'outils, file de tâches, configuration | P2–P6 | `pytest -q` passe hors ligne ; aucun test n'importe `google.genai` réel ni ne contacte Internet (garde `socket` bloqué dans `conftest.py`) |
| V1-TST-02 | Tests d'intégration réels séparés et opt-in | P2 | `pytest -m integration` désactivé par défaut ; `test_live.py` déplacé sous `tests/integration/` (chemin futur) |
| V1-TOOL-01 | Source de vérité unique des 26 outils ; noms et paramètres conservés | P3 | Test de contrat : pour chacun des 26 noms, déclaration ⇔ handler ; instantané JSON des déclarations identique à celui d'aujourd'hui (sauf changement documenté) |
| V1-LIVE-01 | `core/jarvis_live.py` ne contient plus la logique de dispatch ni d'imports d'actions | P3, P4 | Test d'architecture : aucun `from actions` dans `core/jarvis_live.py` ; domaine/agent/mémoire n'importent pas PyQt6 |
| V1-LIVE-02 | Reconnexion fiable : un seul écouteur de raccourci, erreurs fatales vs transitoires testées, erreurs visibles | P4 | Tests avec session factice : 5 reconnexions → 1 seul `keyboard.add_hotkey` ; erreur d'auth → arrêt sans boucle |
| V1-TASK-01 | Cycle de vie des tâches correct : `FAILED`/`ABORTED` exposés, annulation nettoyée, 3 tentatives réelles | P5 | Tests : échec exécuteur → `FAILED` ; annulation en file → retirée ; `analyze_error` autorise la 3ᵉ tentative |
| V1-MEM-01 | Opérations mémoire atomiques et récupérables | P6 | Tests : 50 écritures concurrentes sans perte ; fichier corrompu → `.bak` préservé, pas d'écrasement ; catégorie inconnue rejetée |
| V1-SEC-02 | Plus de `shell=True` alimenté par une valeur du modèle ; plus d'`exec` in-process de code généré | P7 | Recherche statique `shell=True` : seules des chaînes constantes ; `desktop_control(task)` désactivé ou délégué à un sous-processus borné |
| V1-SEC-03 | Contenu non fiable (notifications, pages, fichiers) étiqueté comme donnée ; réponse automatique aux notifications **désactivée par défaut** | P7 | `auto_reply_enabled` par défaut `false` ; test : une notification piégée n'appelle pas `send_message` sans confirmation |
| V1-SEC-04 | Les logs n'enregistrent ni secrets ni texte saisi | P7 | Test : `ActionLogger.log("type", …)` ne persiste pas la valeur |
| V1-UI-01 | Palette de design unique ; comportement visuel inchangé | P8 | Une seule définition des 21 tokens ; captures avant/après identiques (revue visuelle) |
| V1-DEP-01 | Dépendances complètes, sans doublon, installables sur Windows 10/11 propre | P9 | Installation scriptée sur venv vierge ; `python -c "import …"` pour chaque dépendance déclarée ; plus d'import hors `requirements*.txt` |
| V1-DOC-01 | README honnête (licence, OS, capacités) | P9 | Revue : zéro affirmation sans implémentation |
| V1-MIG-01 | Procédure de migration et de retour arrière pour chaque changement risqué | P0–P9 | Chaque phase de `DEVELOPMENT_PHASES.md` contient une section « Retour arrière » exécutée au moins une fois |

### 6.2 Souhaitables (SHOULD)

- Remplacer `print` par une journalisation structurée minimale dans les modules touchés (ADR-017).
- Retirer `logging.basicConfig` de l'import de `autonomy_manager`.
- Conserver `core/autonomy_manager.py` en l'état documenté « expérimental, non branché » et marquer `manage_autonomy` comme tel dans la déclaration d'outil (sans changer son nom).
- `session_resumption` dans `_build_config` **après** validation par un test d'intégration opt-in (comportement non vérifié durant l'audit).

### 6.3 Hors périmètre fonctionnel V1 (WON'T)

Architecture complète de providers ; moteurs locaux texte/voix ; nouveau moteur d'autonomie ; RAG ; permissions exhaustives ; refonte du contrôle de l'ordinateur ; client web ; support multiplateforme livré. (Les correctifs de sécurité ponctuels listés ci-dessus restent autorisés.)

---

## 7. Périmètre V1.5 — Nouvelle architecture IA, autonomie et mémoire

**Pré-requis de démarrage** : la porte de sortie V1 (P9) est validée — voir `DEVELOPMENT_PHASES.md` §« Gate V1 ».

| ID | Exigence | Phase | Critère d'acceptation mesurable |
|---|---|---|---|
| V15-PRV-01 | Registre de providers déclarant des capacités ; aucun module métier n'importe un SDK propriétaire | P10 | Test d'architecture : `google.genai` / `google.generativeai` importés **uniquement** sous `providers/` |
| V15-PRV-02 | Contrats distincts : texte, voix temps réel, STT, TTS, embeddings | P10, P12 | Un faux provider par contrat passe la suite de contrats ; ajout d'un adaptateur = ajout de fichier(s) sous `providers/` sans modification du reste |
| V15-PRV-03 | Routeur de capacités : disponibilité, clé/configuration, mode local/cloud, confidentialité, repli autorisé | P11 | Table de décision testée (≥ 12 cas) ; refus explicite si aucune combinaison ne satisfait la tâche |
| V15-PRV-04 | Adaptateur texte local (candidat : Ollama), modèles chargés à la demande | P11 | Test d'intégration opt-in ; JARVIS démarre et converse en texte sans clé cloud quand le mode local est choisi |
| V15-PRV-05 | STT/TTS locaux facultatifs (candidats : Whisper, Piper) | P12 | Opt-in ; contrainte matérielle documentée ; échec propre si indisponible |
| V15-SEC-01 | `secret_store` + `permission_manager` + `confirmation_policy` appliqués à **toutes** les actions | P13, P14 | Test : aucune action exécutable sans passer par le gestionnaire de permissions (test de couverture sur le registre) |
| V15-SEC-02 | Niveaux d'autonomie `OFF/ASSISTED/SUPERVISED/AUTONOMOUS` formalisés ; interdictions fondamentales intangibles | P13, P15 | Matrice niveau × risque testée (voir `BACKEND_CONTRACT.md` C-13) |
| V15-ACT-01 | Contrat d'action commun (paramètres typés, risque, permissions, effets de bord, vérification, journalisation) | P14 | 26/26 outils migrés ou explicitement exclus avec justification |
| V15-ACT-02 | Adaptateurs de plateforme `platform/windows/` | P14 | Aucun `winreg`/`ctypes`/`pycaw`/`pywinauto`/`winrt` importé hors `platform/windows/` |
| V15-AUT-01 | Un seul moteur Objectif → Plan → Validation → Exécution → Observation → Vérification → Replanification → Résultat | P15 | Suppression de la double file : `agent/task_queue.py` et `core/autonomy_manager.py` fusionnés ou retirés ; test de bout en bout avec faux provider |
| V15-AUT-02 | Étapes typées avec résultats transmissibles ; limites de temps/essais/coût ; annulation, pause, reprise | P15 | Tests de budgets et d'arrêt (timeout, max essais, plafond d'appels) ; reprise après redémarrage depuis l'état persisté |
| V15-CTL-01 | Vérification d'effet réel pour les workflows (application ouverte, fichier créé, message visible) | P16 | Au moins 5 workflows de référence (W-1 à W-5) avec critère de réussite observable (voir `APP_FLOW.md` §F-13 à F-15) |
| V15-MEM-01 | Service mémoire (SQLite + FTS5), migration depuis `long_term.json` avec sauvegarde/restauration | P17 | Migration aller/retour sans perte (test sur jeux de données synthétiques) |
| V15-MEM-02 | RAG local traçable : ingestion autorisée, segmentation, provenance, suppression | P18 | Chaque passage retourné cite sa source ; suppression d'un document retire tous ses segments (test) |
| V15-UI-01 | UI : état des providers, demandes de confirmation, progression des tâches, niveau d'autonomie, erreurs de reprise — sans dégrader le HUD | P19 | Revue visuelle ; zéro régression des parcours V1 |

---

## 8. Capacités reportées à la V2

Support réellement testé de macOS/Linux ; interface web ou autre client ; séparation client / services / moteur ; fournisseurs et modèles supplémentaires ; autonomie et mémoire plus poussées. **Ne sont présentées comme livrées ni en V1 ni en V1.5.**

---

## 9. Exigences non fonctionnelles

### 9.1 Confidentialité

- Aucune donnée personnelle (mémoire, audio, captures, messages) n'est envoyée à un service distant **implicitement** (V1.5 : choix explicite local/cloud par capacité).
- Conservation minimale : pas de rétention automatique des flux audio, captures d'écran ou messages « parce qu'ils existent ».
- Le partage d'écran respecte la liste de blocage et le flou des champs mot de passe ; V1.5 étend ces filtres à **toute** capture (raccourci, `screen_process`, `interact_ui`).
- Les données utilisateur (`memory/`, `logs/`) restent hors dépôt et sauvegardables/restaurables.

### 9.2 Sécurité

- Secrets hors dépôt et hors JSON (ADR-006) ; le `.env` est une **configuration locale, pas un coffre-fort chiffré** — limite documentée.
- Contenus non fiables (pages web, messages, fichiers, notifications, sorties d'outils) = **données**, jamais instructions de sécurité.
- Exécution de code : espace de travail explicite, sous-processus, délais, jamais d'`exec` dans le processus principal ; un filtre AST n'est pas une garantie de sécurité.
- Les actions spontanées suivent **les mêmes contrôles** que les actions demandées.

### 9.3 Fiabilité

- Erreurs compréhensibles, jamais silencieuses ; aucune action déclarée réussie sans preuve (statuts `SUCCEEDED`, `UNVERIFIED`, `FAILED`).
- Reconnexions bornées avec journalisation ; fermeture propre (pas de `os._exit` en V1 sauf repli après délai).
- Mémoire : écriture atomique, sauvegarde rotative, jamais d'écrasement de la dernière bonne copie.

### 9.4 Performance (cibles à mesurer, non mesurées durant l'audit)

- Latence audio perçue non dégradée par le refactoring V1 (comparaison avant/après sur un scénario de référence).
- Les outils longs ne bloquent pas la boucle de réception audio (V1 : exécution déléguée hors de la boucle ; V1.5 : tâches asynchrones annulables).
- Aucun modèle local lourd chargé au démarrage (chargement à la demande).

### 9.5 Maintenabilité

- Dépendances justifiées, épinglées après vérification (aucune version arbitraire).
- Journalisation structurée sans secrets ; tests déterministes ; contrats documentés dans `BACKEND_CONTRACT.md`.

---

## 10. Fonctionnalités exclues (toutes versions tant qu'elles ne sont pas replanifiées)

Migration vers JavaScript/Next.js/backend web (D1) ; serveur vectoriel externe obligatoire ; fonctionnement multi-utilisateur ; stockage automatique de tous les flux audio/écran ; exécution illimitée sans arrêt possible ; « AGI » ou autonomie totale présentées comme acquises.

---

## 11. Définition du succès

| Version | Le succès est atteint quand… |
|---|---|
| **R (immédiat)** | La clé exposée est révoquée, le fichier n'est plus suivi, `.gitignore` couvre les bons chemins, une procédure de purge d'historique est décidée (ADR-006) |
| **V1** | Tous les critères §6.1 passent ; démarrage sous Windows 10/11 sur environnement documenté ; parcours existants conservés (voix, texte, 26 outils, mémoire, partage d'écran, notifications, UI) ; suite offline verte |
| **V1.5** | Tous les critères §7 passent ; aucune référence directe à Gemini hors `providers/` ; un seul moteur d'orchestration ; permissions appliquées partout ; mémoire migrée et RAG traçable ; mode local fonctionnel sans clé cloud |
| **V2** | Non planifiée en détail ; critères à définir après validation V1.5 |

---

## 12. Dépendances entre exigences (extrait)

`V1-SEC-01 → V1-CFG-01 → V1-TST-01 → V1-TOOL-01 → V1-LIVE-01` puis `V1-TASK-01`, `V1-MEM-01`, `V1-SEC-02/03/04` ; gate V1 → `V15-PRV-*` → `V15-SEC-*` → `V15-ACT-*` → `V15-AUT-*` → `V15-CTL-01` ; `V15-MEM-01 → V15-MEM-02` (indépendant de l'autonomie sauf pour l'outil de recherche) ; `V15-UI-01` en dernier.

---

## 13. Questions ouvertes pour la revue CTO (décisions du propriétaire requises)

1. **Licence** : Apache-2.0 (fichier `LICENSE`) ou CC BY-NC 4.0 (README) ? Et attribution amont « FatihMakes / MARK XXXIX » : le code est-il dérivé d'un projet tiers dont la licence impose des mentions ? *(ADR-019, proposé).*
2. **Historique Git** : acceptez-vous une réécriture d'historique (`git filter-repo`) pour purger la clé, sachant que le dépôt est public et que la clé doit de toute façon être considérée compromise ? *(ADR-006).*
3. **Version d'API Gemini** : `run()` utilise `v1alpha`, `test_live.py` `v1beta` ; seul un test d'intégration opt-in peut trancher. *(ADR-022, différé).*
4. **Nom produit** : « JARVIS » vs « MARK XXXIX » dans l'UI/les prompts.
5. **Périmètre des dossiers autorisés** de `file_controller` (actuellement tout `~`).

---

## 14. Limites de vérification de cet audit

- Aucun code exécuté ; aucun test réel contre Gemini Live ; aucun essai sous Windows (environnement d'audit : Linux, Python 3.12).
- `memory/long_term.json` et `memory/USER_*.md` sont ignorés par Git : **format** vérifié par le code, **contenu réel** non vu.
- Actions secondaires non lues ligne à ligne : `flight_finder.py`, `game_updater.py`, `youtube_video.py`, `weather_report.py`, `file_processor.py` (analysés par signature, dépendances et marqueurs ; leur comportement détaillé est marqué « non approfondi » le cas échéant).
- L'historique Git (3 commits) a été inspecté ; aucun autre dépôt ni branche distante n'existe.
