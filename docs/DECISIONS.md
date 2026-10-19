# DECISIONS — Registre des décisions techniques (ADR) de la refonte de JARVIS

| | |
|---|---|
| **Document** | `DECISIONS.md` (6/9) |
| **Base** | `main` @ `2dbb971` |
| **Références** | `PRD.md`, `TRD.md`, `RISKS.md`, `DEVELOPMENT_PHASES.md`, `BACKEND_CONTRACT.md`, `BACKEND_SCHEMA.md`, `APP_FLOW.md`, `DESIGN_SYSTEM.md` |

**Statuts** : *accepté* (décision CTO, applicable) · *proposé* (attend l'arbitrage du propriétaire) · *différé* (décidable seulement après une mesure) · *remplacé*. Tout écart avec une décision du mandat CTO est signalé comme **ÉCART JUSTIFIÉ**.

## Index

| ADR | Titre | Statut | Version |
|---|---|---|---|
| 001 | Découpage V1 / V1.5 / V2 | accepté | toutes |
| 002 | Modularisation progressive plutôt que réécriture totale | accepté | V1 → V1.5 |
| 003 | Stack et plateforme conservées (Python, PyQt6, Windows) | accepté | V1 |
| 004 | Architecture par contrats et adaptateurs de providers | accepté | V1.5 |
| 005 | Séparation des capacités texte / voix temps réel / STT / TTS / embeddings + routeur | accepté | V1.5 |
| 006 | Secrets : `.env` non versionné, limites assumées, clé exposée, purge d'historique | accepté (purge : **proposé**) | R + V1 |
| 007 | Un seul moteur d'exécution ; autonomie à quatre niveaux | accepté | V1.5 |
| 008 | Politique de permissions et de confirmations | accepté (stopgap V1) | V1 / V1.5 |
| 009 | Mémoire : RAG local progressif (SQLite + FTS5, vectoriel facultatif) | accepté | V1.5 |
| 010 | Windows d'abord ; adaptateurs `platforms/` — **ÉCART JUSTIFIÉ** de nom | accepté | V1 / V1.5 |
| 011 | Tests sans secret ni réseau | accepté | V1 |
| 012 | Préservation des capacités et de l'identité visuelle | accepté | V1 |
| 013 | Registre d'outils = source de vérité | accepté | V1 / V1.5 |
| 014 | Étapes de plan typées et transmission de résultats | accepté | V1.5 |
| 015 | Limites d'exécution : code généré et périmètres d'accès | accepté (racines fichiers : **proposé**) | V1 / V1.5 |
| 016 | Contenus non fiables = données | accepté | V1 / V1.5 |
| 017 | Observabilité : journaux structurés sans secrets | accepté | V1 / V1.5 |
| 018 | `pyproject.toml` : outillage en V1, packaging en V1.5 — **ÉCART JUSTIFIÉ** | accepté | V1 / V1.5 |
| 019 | Licence et attribution | **proposé** | V1 |
| 020 | Migration et retour arrière | accepté | toutes |
| 021 | UI : PyQt6 conservé ; overlay Tk conservé en V1, remplacement évalué en V1.5 | accepté / proposé | V1 / V1.5 |
| 022 | Version d'API Gemini Live et `session_resumption` | **différé** | V1 |
| 023 | Stdlib d'abord : `dataclasses`, `enum`, `sqlite3` | accepté | V1 / V1.5 |

---

## ADR-001 — Découpage V1 / V1.5 / V2

- **Statut** : accepté · **Version** : toutes.
- **Contexte** : le projet existant fonctionne (au moins pour son auteur) mais mélange stabilisation, nouvelles architectures et ambitions « AGI » (`implementation.md`, `phases.md`).
- **Problème** : sans frontière nette, la refonte devient une réécriture simultanée, non testable et non réversible.
- **Décision** : **V1** = refonte et stabilisation des composants existants (+ remédiations de sécurité) ; **V1.5** = nouvelle architecture IA (providers, autonomie unifiée, permissions, contrôle fiabilisé, RAG) ; **V2** = extensions (autres OS, client web, providers supplémentaires). Matrice unique : `PRD.md` §5.
- **Alternatives** : (a) une seule grande version ; (b) V1 incluant les providers (rejetée : risque R-F13).
- **Raisons** : continuité, réversibilité, preuves de stabilité avant d'ajouter des abstractions.
- **Conséquences** : (+) livraisons testables, gates claires ; (−) certaines faiblesses (confirmation, autonomie) ne sont traitées qu'en stopgap en V1.
- **Fichiers concernés** : tout le dépôt ; `core/jarvis_live.py`, `agent/*`, `memory/*`.
- **Réévaluation** : si la gate V1 échoue deux fois pour une même cause.

## ADR-002 — Modularisation progressive plutôt que réécriture totale

- **Statut** : accepté · **Version** : V1 → V1.5.
- **Contexte** : 16 900 lignes Python ; `core/jarvis_live.py` importe 25 modules (C1).
- **Problème** : couplage fort ; mais les 26 outils représentent un acquis fonctionnel.
- **Décision** : méthode « étrangler » : shim → bascule appelant par appelant → suppression après gate ; un commit par intention ; caractérisation avant modification (`TRD.md` §13).
- **Alternatives** : réécriture complète (rejetée : perte de fonctionnalités, aucun filet de tests) ; refactoring opportuniste sans plan (rejeté : dérive).
- **Raisons** : sécurité de la migration ; chaque phase livrable.
- **Conséquences** : (+) retour arrière facile ; (−) présence temporaire de shims (dette contrôlée, retirés en P19).
- **Fichiers** : `core/jarvis_live.py`, `core/tools.py`, `config/__init__.py`, `logs/action_logger.py`.
- **Réévaluation** : si un shim survit à la gate V1.5.

## ADR-003 — Stack et plateforme conservées

- **Statut** : accepté · **Version** : V1.
- **Décision** : Python (**3.11 minimum**, exigé par `asyncio.TaskGroup` utilisé dans `JarvisLive.run` ; 3.12 visé), PyQt6, Windows 10/11 ; Gemini Live comme référence de compatibilité ; **aucune** migration vers JavaScript/Next.js/backend web.
- **Alternatives** : Electron/Next.js (rejeté : coût sans bénéfice produit) ; PySide6 (rejeté : sans raison).
- **Conséquences** : (+) pas de réécriture de l'UI ; (−) dépendance à PyQt6 et à des bibliothèques Windows.
- **Fichiers** : `main.py`, `ui/*`, `requirements.txt`.
- **Réévaluation** : lorsque V2 vise un client web (voir ADR-021).

## ADR-004 — Architecture par contrats et adaptateurs de providers

- **Statut** : accepté · **Version** : V1.5 (P10).
- **Contexte** : appels directs à `google.genai` et `google.generativeai` dans ≥ 10 modules (C4, C7).
- **Problème** : changer de fournisseur obligerait à réécrire l'application ; impossible de tester sans réseau.
- **Décision** : contrats stables sous `providers/` (C-02…C-07) ; la logique métier n'importe **aucun** SDK propriétaire ; les SDK sont confinés dans les adaptateurs. V1 se limite aux frontières utiles à la testabilité (`UiPort`, dispatcher), **sans** registre de providers.
- **Alternatives** : abstraction dès V1 (rejetée : ADR-001) ; « wrapper léger » unique (rejeté : ne distingue pas les capacités).
- **Raisons** : interchangeabilité local/cloud ; tests par fakes.
- **Conséquences** : (+) ajout d'un provider = ajout de fichiers ; (−) coût de migration de 10 modules (P10).
- **Fichiers** : `core/utils.py`, `agent/{planner,executor,error_handler}.py`, `actions/{code_helper,dev_agent,desktop,screen_processor}.py`, `test_live.py`.
- **Critère de fin** : un registre de providers **sans** appels directs à Gemini ailleurs n'est pas « terminé » si un appel subsiste (gate V1.5).
- **Réévaluation** : si le nombre de providers reste 1 après V1.5.

## ADR-005 — Séparation des capacités et routeur

- **Statut** : accepté · **Version** : V1.5 (P10-P12).
- **Décision** : cinq familles de capacités distinctes — génération de texte, voix temps réel, STT, TTS (+ mot d'activation), embeddings ; chaque provider **déclare** ses capacités et limites ; le routeur choisit selon : disponibilité, clé/configuration, capacités requises, mode local/cloud, confidentialité, coût/limites connus, replis autorisés. **Jamais** : « fournisseur textuel ⇒ voix ou outils ».
- **Stratégie pragmatique** : conserver Gemini Live (voix cloud) ; ajouter le contrat texte ; adaptateurs **candidats** locaux (Ollama ; Whisper/Piper) — **non intégrés aujourd'hui**, à valider par mesures matérielles (Q3).
- **Alternatives** : un seul « super-provider » (rejeté) ; routage statique par configuration (rejeté : pas de repli).
- **Conséquences** : (+) honnêteté des capacités ; (−) complexité du routeur (tests tabulaires).
- **Fichiers** : `core/utils.py`, `actions/screen_processor.py` (vision via session Live séparée).
- **Réévaluation** : si un provider unifie texte+voix+embeddings au point de rendre le routeur superflu.

## ADR-006 — Secrets : `.env`, limites, clé exposée, purge d'historique

- **Statut** : accepté ; sous-décision « purge d'historique » **proposée**.
- **Contexte** : `ui/config/api_keys.json` versionné (R-O01) ; chemins incohérents (R-O02) ; `.gitignore` erroné (R-O03).
- **Décision** :
  1. **Aucun secret dans un JSON de configuration** ; `.env` non versionné + `.env.example` factice ; variable d'environnement prioritaire ; priorité : env > `.env` profil > `.env` racine > erreur (`TRD.md` §6.2) ;
  2. réécriture ciblée d'une clé sans effacer les autres ; écriture atomique ; permissions Windows en meilleur effort ; rotation/effacement documentés ;
  3. un provider local ne requiert aucune clé cloud ;
  4. **limite assumée** : `.env` ≠ coffre chiffré ; adaptateur Windows Credential Manager **facultatif** (V1.5, P13), jamais obligatoire ;
  5. **la clé exposée est révoquée immédiatement** (P0) — elle est tenue pour compromise, quelle que soit la suite ;
  6. **proposé** : purge de l'historique par `git filter-repo` (réécriture + force-push) — utile pour l'hygiène du dépôt public, **sans effet sur la compromission** (copies/forks possibles).
- **Alternatives** : keyring/Credential Manager obligatoire (rejeté : complexité, V1) ; fichier chiffré maison (rejeté : fausse sécurité).
- **Conséquences** : (+) fin de la fuite par Git ; (−) clé en clair sur disque local.
- **Fichiers** : `ui/config/api_keys.json`, `.gitignore`, `core/utils.py`, `memory/config_manager.py` (mort), `ui/interface.py`, `config/__init__.py`.
- **Réévaluation** : distribution à des tiers (alors keyring obligatoire).

## ADR-007 — Un seul moteur d'exécution ; autonomie à quatre niveaux

- **Statut** : accepté · **Version** : V1.5 (P15) ; V1 : fiabilisation et honnêteté.
- **Contexte** : `agent/task_queue.py` (réel, limité) et `core/autonomy_manager.py` (simulation non alimentée) prennent chacun des décisions d'exécution (R-O09).
- **Décision** : un **moteur unique** (`agent/engine.py`) : Objectif → Plan → Validation → Exécution → Observation → Vérification → Replanification → Résultat ; les objectifs proactifs rejoignent **la même file et la même politique de permissions** ; niveaux `OFF / ASSISTED / SUPERVISED / AUTONOMOUS` (comportements exacts : `BACKEND_CONTRACT.md` C-13) ; aucun niveau ne désactive les interdictions fondamentales ; budgets (temps, essais, replans, appels modèle) obligatoires.
- **V1** : documenter l'autonomie comme **expérimentale non alimentée**, retirer l'effet de bord `basicConfig`, exiger une confirmation pour `manage_autonomy(enable)`.
- **Alternatives** : conserver deux moteurs (rejeté : décisions concurrentes) ; booléen `enabled` (rejeté : insuffisant).
- **Conséquences** : (+) traçabilité ; (−) suppression de fichiers existants (`agent/task_queue.py`, `core/autonomy_manager.py`) à la fin de P15.
- **Fichiers** : `agent/*`, `core/autonomy_manager.py`, `actions/manage_autonomy.py`, `core/jarvis_live.py`.
- **Réévaluation** : si les budgets ne suffisent pas à contenir les dérives (R-F02).

## ADR-008 — Politique de permissions et de confirmations

- **Statut** : accepté · **Version** : V1 (stopgap) puis V1.5 (P13).
- **Décision** : niveaux de risque `LOW / MEDIUM / HIGH / CRITICAL` portés par chaque action ; décision `ALLOW | CONFIRM | DENY` fonction de (risque, niveau d'autonomie, **origine** : `user | autonomy | notification | memory`) ; confirmations générées par le système à partir de paramètres validés ; expiration = refus ; journal de chaque décision. **V1** : stopgap strictement limité à 6 familles d'actions (P7) et **explicitement transitoire** (pas de logique de risque nouvelle).
- **Alternatives** : permissions exhaustives dès V1 (rejeté : hors périmètre V1) ; confirmation par le modèle (rejeté : le modèle n'est pas une frontière de confiance).
- **Conséquences** : (+) actions spontanées = mêmes contrôles ; (−) friction (R-F09).
- **Fichiers** : `ui/screen_overlay.py` (`confirm_action`), `config/app_profiles.json` (`confirm_critical_actions`), `core/prompt.txt`.
- **Réévaluation** : après 2 semaines d'usage réel (taux de refus/validation).

## ADR-009 — Mémoire : RAG local progressif

- **Statut** : accepté · **Version** : V1 (stabiliser) ; V1.5 (P17-P18).
- **Décision** : trois besoins distincts — mémoire **structurée** (préférences, identité, projets…), **épisodique**, **recherche documentaire** ; un RAG ne remplace pas la structure (contradictions, suppression). Stockage local **SQLite + FTS5** (stdlib) ; recherche lexicale immédiatement utilisable ; **vectoriel facultatif** si la pertinence mesurée le justifie (Q4) ; embeddings via un contrat distinct ; ingestion **autorisée** uniquement ; provenance et suppression tracées ; aucun envoi distant implicite ; pas de conservation automatique audio/écran/messages. Migration depuis `long_term.json` avec sauvegarde/restauration (ADR-020).
- **Alternatives** : serveur vectoriel externe (rejeté : lourdeur) ; vectoriel seul (rejeté : opacité) ; garder le JSON (rejeté : pas de recherche).
- **Conséquences** : (+) local, traçable ; (−) migration à sécuriser (R-F06).
- **Fichiers** : `memory/memory_manager.py`, `memory/long_term.json`, `memory/USER_*.md`.
- **Réévaluation** : si FTS5 seul atteint la pertinence cible → pas de vectoriel.

## ADR-010 — Windows d'abord ; adaptateurs `platforms/`

- **Statut** : accepté · **Version** : V1 (périmètre), V1.5 (adaptateurs).
- **Contexte** : 57 branchements de plateforme et ≥ 20 usages Windows disséminés (C9).
- **Décision** : V1 = **Windows 10/11 uniquement** ; V1.5 isole les appels système derrière des adaptateurs stables ; macOS/Linux = V2.
- **ÉCART JUSTIFIÉ vs arbre du mandat** : le dossier `platform/windows/` est renommé **`platforms/windows/`**, car un paquet racine nommé `platform` **masque le module standard `platform`** (importé notamment par `ui/interface.py`, `actions/file_controller.py`, `actions/desktop.py`) dès que l'application démarre depuis la racine.
- **Alternatives** : `os_adapters/`, `system/` (équivalentes ; `platforms/` retenu pour sa proximité sémantique).
- **Conséquences** : (+) pas d'ombrage de la stdlib ; (−) écart documenté avec le mandat.
- **Réévaluation** : lors du premier portage d'un second OS.

## ADR-011 — Tests sans secret ni réseau

- **Statut** : accepté · **Version** : V1 (P1.0/P2).
- **Décision** : suite par défaut **hors ligne**, sans clé ; garde `socket` dans `conftest.py` ; intégrations réelles **opt-in** (`-m integration`) ; couches : unitaire, contrat, architecture, UI offscreen, effets de bord, migration ; fakes plutôt que mocks ad hoc ; données synthétiques uniquement.
- **Alternatives** : tester contre l'API réelle en CI (rejeté : secret, coût, instabilité).
- **Conséquences** : (+) reproductibilité ; (−) effort de fakes (`FakeLiveSession`…).
- **Fichiers** : `test_live.py` (déplacé vers `tests/integration/`).
- **Réévaluation** : quand une CI avec secrets protégés est disponible (toujours opt-in).

## ADR-012 — Préservation des capacités et de l'identité visuelle

- **Statut** : accepté · **Version** : V1.
- **Décision** : les 26 outils conservent **noms et paramètres** (exceptions listées : `TRD.md` §13.3 et `agent_task.action` en P5) ; l'identité HUD (bleu-noir, cyan, accents orange, Courier New) est préservée : V1 clarifie les composants (`ui/theme.py`) **sans** redessiner ; V1.5 ajoute le strict nécessaire (providers, permissions, tâches, autonomie).
- **Alternatives** : refonte visuelle (rejetée).
- **Conséquences** : (+) pas de régression perçue ; (−) mélange PyQt6/Tk conservé (ADR-021).
- **Fichiers** : `core/tools.py`, `ui/*`.
- **Réévaluation** : V2 (client web).

## ADR-013 — Registre d'outils = source de vérité

- **Statut** : accepté · **Version** : V1 (P3), V1.5 (P14).
- **Contexte** : R-O10 (deux dispatchers, deux déclarations).
- **Décision** : `core/tool_registry.py` est la **source unique** (nom, schéma modèle, handler par chemin dotté, métadonnées) ; `core/tools.py` devient une **vue générée** (`TOOL_DECLARATIONS` inchangé) ; le planificateur dérive sa liste du registre (drapeau `planner`) ; V1.5 : `ActionSpec` complet (risque, permissions, vérification).
- **Alternatives** : décorateurs `@tool` dans chaque action (reporté : impose de modifier 25 modules en V1).
- **Conséquences** : (+) cohérence testable ; (−) migration des branches spéciales de `_execute_tool`.
- **Fichiers** : `core/tools.py`, `core/jarvis_live.py`, `agent/executor.py`, `agent/planner.py`.
- **Réévaluation** : si les handlers gagnent à vivre avec leur schéma (décorateurs) en V1.5.

## ADR-014 — Étapes de plan typées et transmission de résultats

- **Statut** : accepté · **Version** : V1.5 (P15) ; V1 : comportement existant documenté.
- **Contexte** : le planificateur impose « ne jamais référencer les résultats précédents » alors que `_inject_context` les injecte (avec traduction) dans `file_controller`.
- **Décision** : chaque étape déclare `produces` (valeurs nommées et typées) et `consumes` ; l'exécuteur valide les types ; **les restrictions de sécurité ne sont pas supprimées** pour autoriser les dépendances : la sécurité reste portée par les permissions et la validation, pas par l'interdiction de lier des étapes.
- **V1** : conserver `_inject_context` tel quel (documenté) ; aucune nouvelle liaison.
- **Alternatives** : interpolation textuelle libre `{{step1.result}}` (rejetée : injection) .
- **Conséquences** : (+) tâches dépendantes fiables ; (−) planificateur plus strict (plus d'échecs de validation).
- **Fichiers** : `agent/planner.py`, `agent/executor.py`.
- **Réévaluation** : si le taux d'échec de validation des plans est excessif.

## ADR-015 — Limites d'exécution : code généré et périmètres d'accès

- **Statut** : accepté (code généré) ; **proposé** (racines de `file_controller`).
- **Contexte** : R-O05, R-O06, R-O26.
- **Décision (accepté)** : (1) **plus aucun `exec` de code généré dans le processus principal** (`desktop_control(task)` désactivé par défaut en V1) ; (2) le filtre AST (`_check_code_safety`) est **une heuristique**, jamais une garantie ; (3) exécution de code = sous-processus, **espace de travail explicite**, délais, sortie tronquée, liste d'exécutables, liste blanche de paquets (V1.5 : permissions/réseau) ; (4) toute exécution de script non Python exige confirmation (stopgap V1).
- **Décision (proposé)** : racines autorisées de `file_controller` : `Desktop, Documents, Downloads, Pictures, Music, Videos, ~/JarvisProjects` (au lieu de tout `~`).
- **Alternatives** : bac à sable OS (conteneur/AppContainer) — à étudier en V2 ; interdiction totale de l'exécution de code (rejetée : perte de `code_helper`/`dev_agent`).
- **Conséquences** : (+) réduction forte de la surface ; (−) fonctionnalités `desktop_control(task)` limitées.
- **Fichiers** : `actions/desktop.py`, `actions/code_helper.py`, `actions/dev_agent.py`, `agent/executor.py`, `actions/file_controller.py`.
- **Réévaluation** : disponibilité d'un vrai bac à sable.

## ADR-016 — Contenus non fiables = données

- **Statut** : accepté · **Version** : V1 (notifications, navigateur) / V1.5 (général).
- **Décision** : pages web, messages, fichiers importés, notifications, sorties d'outils, passages RAG/mémoire sont des **données** (`<untrusted source="…">`) ; ils ne peuvent **ni** modifier permissions, niveau d'autonomie, liste d'outils ou configuration, **ni** constituer une instruction de sécurité ; les actions qui en découlent suivent la confirmation.
- **Alternatives** : filtrage heuristique par mots-clés (rejeté : contournable).
- **Conséquences** : (+) défense en profondeur ; (−) le modèle peut ignorer l'étiquette → la **barrière réelle** est la permission (ADR-008), pas le prompt.
- **Fichiers** : `core/notification_manager.py`, `actions/browser_control.py`, `actions/get_context.py`.
- **Réévaluation** : tests d'injection (R-F11).

## ADR-017 — Observabilité

- **Statut** : accepté · **Version** : V1 (minimal), V1.5 (événements).
- **Décision** : une configuration de journalisation unique (plus de `basicConfig` à l'import) ; événements structurés JSONL (`tool.start/end/error`, décisions de permission, tâches) ; **aucun** secret, contenu de message privé ou texte tapé ; identifiants de tâche/étape ; rotation.
- **Alternatives** : `print` (rejeté).
- **Conséquences** : (+) diagnostic honnête de ce qu'une tâche a réellement accompli ; (−) discipline de masquage.
- **Fichiers** : `logs/action_logger.py`, `core/autonomy_manager.py`, tout `print`.
- **Réévaluation** : volume de logs.

## ADR-018 — `pyproject.toml` : outillage V1, packaging V1.5

- **Statut** : accepté · **Version** : V1 / V1.5.
- **ÉCART JUSTIFIÉ vs le mandat** (« V1 ou transition V1.5, à justifier ») : en **V1**, `pyproject.toml` ne contient que l'**outillage** (pytest, ruff) — amorce en P1.0 ; la **source d'installation reste `requirements*.txt`** (setup.py existant conservé) ; le **packaging** (extras `local`, `rag`, `windows`, `dev`) est introduit en **P10**, quand des dépendances optionnelles justifient réellement des extras.
- **Raison** : éviter de changer l'installation pendant la stabilisation.
- **Alternatives** : packaging complet dès V1 (rejeté) ; ne jamais migrer (rejeté : extras nécessaires en V1.5).
- **Réévaluation** : P10.

## ADR-019 — Licence et attribution

- **Statut** : **proposé** (décision du propriétaire).
- **Contexte** : `LICENSE` = Apache-2.0 ; `readme.md` = CC BY-NC 4.0 ; UI : « FatihMakes Industries · MARK XXXIX · © FATIHMAKES » ; planificateur/erreurs nomment « MARK XXXIX ».
- **Problème** : message légal contradictoire ; provenance éventuelle d'une base amont **non établie** par l'audit.
- **Décision proposée** : (1) le propriétaire confirme l'origine du code ; (2) une seule licence est affichée (README, LICENSE, UI) ; (3) si une base amont existe, ses mentions/licence sont respectées et reproduites ; (4) retrait ou conservation du nom « MARK XXXIX » tranché explicitement.
- **Conséquences** : bloque la rédaction définitive du README (P9) et du pied de page (P8).
- **Fichiers** : `LICENSE`, `readme.md`, `ui/interface.py` (pied de page, titre), `agent/planner.py`, `agent/error_handler.py`, `setup.py`.
- **Réévaluation** : si une licence amont est découverte.

## ADR-020 — Migration et retour arrière

- **Statut** : accepté · **Version** : toutes.
- **Décision** : toute migration de **données** (config, mémoire, tâches) suit : sauvegarde horodatée hors dépôt → `--dry-run` → application → vérification → conservation de la source jusqu'à validation → procédure `--rollback` testée ; toute migration de **code** : tag `pre-P<n>`, drapeaux de repli internes jusqu'à la gate, commits atomiques réversibles.
- **Alternatives** : migration « à la volée » sans sauvegarde (rejetée).
- **Conséquences** : (+) pas de perte ; (−) étapes supplémentaires.
- **Fichiers** : `memory/*`, `config/*`.
- **Réévaluation** : jamais sans incident.

## ADR-021 — UI : PyQt6 conservé ; overlay Tk

- **Statut** : accepté (PyQt6, `_RootShim`) ; **proposé** (remplacement de l'overlay Tk).
- **Contexte** : fenêtre PyQt6 ; `ScreenOverlay` en Tkinter (un `tk.Tk()` par marqueur, dans des threads) ; `JarvisUI.root` = `_RootShim` imitant l'API Tk (`mainloop`, `protocol`).
- **Décision** : V1 : PyQt6 conservé, `_RootShim` conservé (compatibilité de `main.py`), overlay Tk **inchangé** ; V1.5 (P19) : **évaluer** un overlay Qt (marqueur de clic, confirmation) ; **pas** d'interface web ni de remplacement de PyQt6 en V1.
- **Alternatives** : réécrire l'UI (rejeté) ; supprimer l'overlay (rejeté : aperçu avant clic utile).
- **Conséquences** : (+) pas de régression ; (−) fragilité Tk hors thread principal subsiste.
- **Fichiers** : `ui/screen_overlay.py`, `ui/interface.py`, `main.py`.
- **Réévaluation** : P19.

## ADR-022 — Version d'API Gemini Live et `session_resumption`

- **Statut** : **différé** (mesure requise).
- **Contexte** : `JarvisLive.run` utilise `api_version="v1alpha"` ; `test_live.py` `v1beta` et configure `session_resumption` ; `_build_config` ne le configure pas ; `screen_processor` utilise un autre modèle (`…native-audio-preview-12-2025`).
- **Problème** : l'audit statique ne permet pas de savoir lequel est correct ni si la reprise de session est opérationnelle.
- **Décision** : ne rien changer avant un test d'intégration opt-in (P4) comparant les deux versions ; centraliser ensuite le nom de modèle et la version dans la configuration du provider (P10).
- **Réévaluation** : résultat du test d'intégration.

## ADR-023 — Stdlib d'abord : `dataclasses`, `enum`, `sqlite3`

- **Statut** : accepté · **Version** : V1 / V1.5.
- **Décision** : modèles de données internes en `dataclasses` + `enum.StrEnum` (Python ≥ 3.11) ; persistance des tâches et de la mémoire V1.5 avec `sqlite3` (stdlib) ; **aucune** nouvelle dépendance de validation (pas de `pydantic`) tant qu'un besoin mesuré ne l'impose ; validation des paramètres d'outils par le schéma du registre (fonction maison minimale).
- **Alternatives** : `pydantic` (rejeté : dépendance, pas de besoin démontré) ; `attrs`.
- **Conséquences** : (+) installation légère ; (−) validation à écrire et tester.
- **Fichiers** : futurs `agent/models.py`, `memory/models.py`, `core/tool_registry.py`.
- **Réévaluation** : si la validation devient coûteuse à maintenir.

---

## Cohérence inter-documents (contrôle)

| Décision | Document(s) qui l'appliquent |
|---|---|
| ADR-001 | `PRD.md` §5 ; `DEVELOPMENT_PHASES.md` §0.1 |
| ADR-004/005 | `TRD.md` §3 ; `BACKEND_CONTRACT.md` C-02…C-07 ; P10-P12 |
| ADR-006 | `PRD.md` §4 ; `TRD.md` §6 ; P0, P1, P13 ; `RISKS.md` R-O01-03 |
| ADR-007/008 | `APP_FLOW.md` F-09/F-10/F-16 ; `BACKEND_CONTRACT.md` C-10…C-13 ; P5, P7, P13, P15 |
| ADR-009/020 | `BACKEND_SCHEMA.md` §Mémoire ; P6, P17, P18 |
| ADR-010 | `TRD.md` §3.3, §11 ; `BACKEND_CONTRACT.md` C-18 ; P14 |
| ADR-013/023 | `BACKEND_CONTRACT.md` C-08 ; `BACKEND_SCHEMA.md` §Outils ; P3, P14 |
| ADR-015/016 | `TRD.md` §10 ; `RISKS.md` R-O04…R-O08 ; P7 |
| ADR-019/021 | `DESIGN_SYSTEM.md` §8, §9 ; P8, P9, P19 |
