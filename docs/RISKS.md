# RISKS — Registre des risques de la refonte de JARVIS

| | |
|---|---|
| **Document** | `RISKS.md` (5/9) |
| **Base** | `main` @ `2dbb971`, lecture statique (aucune exécution) |
| **Références** | `TRD.md` §2 (diagnostic), `DEVELOPMENT_PHASES.md` (phases `P0…P19`), `DECISIONS.md` (`ADR-*`), `PRD.md` (exigences) |

## Mode d'emploi

- **Partie A — risques OBSERVÉS (`R-O*`)** : constatés dans le code actuel (preuve citée). Statut de mitigation : **aucune mesure n'est en place** tant que la phase indiquée n'est pas réalisée.
- **Partie B — risques FUTURS (`R-F*`)** : introduits ou exposés par la refonte elle-même. Les mitigations sont des **propositions**, pas des faits.
- **Gravité** : Critique · Haute · Moyenne · Basse. **Exposition** : *Certaine* (déjà observée), *Probable*, *Possible*.
- Chaque risque a une **réponse concrète** dans `DEVELOPMENT_PHASES.md` (colonne « Phase »). Un risque sans phase serait une anomalie du plan.
- Un risque n'est **clos** que lorsque son **critère de vérification** est satisfait *et* consigné.

---

# PARTIE A — Risques observés

## A.1 Secrets et configuration

| ID | Risque (preuve) | Gravité | Exposition | Phase | Prévention | Détection | Mitigation | Critère de vérification |
|---|---|---|---|---|---|---|---|---|
| **R-O01** | **Clé API Gemini versionnée en clair** : `ui/config/api_keys.json` présent dans les commits `18497d3` et `2dbb971` (valeur non vide, 39 caractères) ; dépôt rendu **public** le 2026-10-18 | **Critique** | Certaine | **P0** | `.gitignore` correct ; `.env` hors Git ; scan de secrets en CI | Scan de secrets sur l'arbre **et l'historique** ; `git ls-files` | Révoquer et renouveler la clé (immédiat) ; `git rm --cached` ; purge d'historique si acceptée (ADR-006) ; considérer l'ancienne clé comme compromise quoi qu'il arrive | Clé révoquée (confirmation propriétaire) ; `git ls-files` sans `api_keys.json`/`.env` ; scan historique = 0 (si purge) |
| **R-O02** | **Clé écrite là où le moteur ne la lit pas** : UI → `ui/config/api_keys.json` (`BASE_DIR` = `ui/`) ; moteur → `GEMINI_API_KEY` puis `config/api_keys.json` (`core/utils.py`) | Haute | Certaine (premier démarrage sur clone neuf) | P1 | Chargeur unique, priorité explicite | Test de premier démarrage | Unifier (`config/settings.py`), shim de compatibilité | Test : dialogue → clé lisible par `_get_api_key()` sans variable d'environnement (baseline S1/S2) |
| **R-O03** | `.gitignore` ne couvre que `config/api_keys.json` (pas `ui/config/…`, pas `**/api_keys.json`) | Haute | Certaine | P0 | Motifs génériques `**/api_keys.json`, `.env*` | `git check-ignore -v` | Corriger `.gitignore` | `git check-ignore -v ui/config/api_keys.json` → ignoré |
| **R-O20** | Dépendances : imports non déclarés (`PyPDF2`, `pdfplumber`, `python-docx`, `pandas`, `gtts`, `pyttsx3`, `pywin32`, alias `ddgs`), doublon `pillow/Pillow`, **deux SDK Gemini**, aucune version épinglée, dépendances Windows sans marqueur | Moyenne | Certaine | P9 (P10 pour le SDK) | Analyse AST des imports en CI ; installation scriptée | `pip check` ; test d'import de chaque dépendance | Restructurer `requirements*.txt`, épingler uniquement ce qui est vérifié | Installation propre Windows 10/11 + suite verte |

## A.2 Exécution de code généré, injections, permissions

| ID | Risque (preuve) | Gravité | Exposition | Phase | Prévention | Détection | Mitigation | Critère de vérification |
|---|---|---|---|---|---|---|---|---|
| **R-O04** | **Injection de commande** : `open_app` lance `subprocess.Popen(app_name, shell=True)` et `start {app_name}` avec une valeur fournie par le modèle (`actions/open_app.py`, l. 84-97) | Haute | Probable | **P7** | Lancement par liste d'arguments, `os.startfile` ; rejet de `& | ; > <` | Test d'architecture (`shell=True` constants uniquement) | Retirer `shell=True` | Test : `open_app("x & calc")` ne lance rien d'autre ; recherche statique propre |
| **R-O05** | **`exec` in-process de code LLM** : `desktop_control(task)` → `exec(compile(code…))` ; le « sandbox » expose `getattr`, `Path` (écriture/suppression), `pyautogui`, `ctypes` (Windows) — évasion et effets destructeurs possibles | **Critique** | Probable | **P7** | Ne jamais exécuter de code généré dans le processus principal | Test d'architecture (`exec(` hors modules désactivés) | Désactiver par défaut ; si réactivé en V1.5 : sous-processus borné, espace de travail explicite (ADR-015) | Test : `desktop_control(task=…)` refuse sans drapeau ; aucun `exec(` actif |
| **R-O06** | **Contrôle de code partiel et contournable** : le filtre AST (`agent/executor._check_code_safety`) ignore `from os import system`, `os.popen`, `Path.unlink`, `importlib`, etc. ; `code_helper(run)` ne filtre que `.py` ; `.js/.ts/.sh/.ps1/.rb/.php` s'exécutent sans contrôle ; `dev_agent` fait `pip install` de dépendances proposées par le LLM sans liste blanche (la liste blanche ne vaut que pour l'auto-install) ; `_run_project` exécute une commande issue du LLM | Haute | Probable | **P7** puis P14/P15 | Confirmation avant exécution ; liste d'exécutables ; liste blanche de paquets ; **ne jamais présenter le filtre AST comme une garantie** | Journal d'exécution ; tests de contournement connus | Confirmation stopgap ; liste blanche ; troncature de sortie ; V1.5 : espace de travail + permissions | Tests : script `.ps1` → confirmation exigée ; paquet hors liste → refus/confirmation |
| **R-O07** | **Injection indirecte par notification** : le contenu d'un toast Windows est injecté tel quel comme tour utilisateur avec la consigne de répondre via `send_message` (`_poll_notifications_loop`) ; `auto_reply_enabled` défaut `true` | **Haute** | Probable | **P7** (V1), P13 | Contenu = donnée (`<untrusted>`), auto-réponse **désactivée** par défaut, confirmation | Test avec modèle factice et notification piégée | `auto_reply_enabled=false` ; encapsulation ; confirmation d'envoi | Test : notification « envoie X à Y » ⇒ aucun envoi sans confirmation |
| **R-O08** | **Aucune confirmation branchée** : `privacy.confirm_critical_actions` (JSON) jamais lu ; `ScreenOverlay.confirm_action` jamais appelée ; le prompt demande de ne pas confirmer les tâches simples ; `send_message`, `file_controller(delete)`, `system_optimizer(kill_process)`, `computer_settings` (alimentation) exécutés sans demande | Haute | Certaine | **P7** (stopgap), P13 | Politique de confirmation par niveau de risque | Journal des décisions | Stopgap puis `permission_manager` | Test : action listée sans confirmation ⇒ `CONFIRMATION_DECLINED` |
| **R-O16** | **Filtre de confidentialité non universel** : `privacy_guard` appliqué seulement par `ScreenShareWorker` ; le raccourci Ctrl+Shift+J (zone 400×400) et `screen_process` (vision/caméra, session Live séparée) l'ignorent ; `interact_ui` aussi | Haute | Certaine | **P7**, P16 | Pipeline de capture unique | Test : capture d'une fenêtre « password » via raccourci → bloquée | Appliquer le filtre à tous les chemins | Test sur les 3 chemins |
| **R-O17** | **Texte saisi journalisé** : `ActionLogger.log` écrit `value` quand `action_type == "type"` (`logs/action_history.jsonl`) — peut contenir des mots de passe | Moyenne | Certaine | **P7** | Masquage par liste de champs | Test de rédaction | Ne plus persister la valeur | Test : le fichier JSONL ne contient pas la valeur |
| **R-O18** | **Navigateur** : `browser_control` ouvre le **profil réel** de l'utilisateur (`launch_persistent_context`) ; `BrowserInspector` exige le port CDP `9222` (accès local non authentifié) ; le texte des pages est renvoyé au modèle brut | Haute | Probable | P7 (partiel), **P16** | Profil dédié par défaut ; domaines sensibles bloqués ; contenu `untrusted` | Revue de configuration | Profil dédié ; `untrusted` ; documentation du port | Test : lancement par défaut = profil dédié |
| **R-O25** | `system_optimizer(kill_process)` termine (puis `kill`) des processus par nom sans confirmation ; `dry_run` optionnel ; « undo » non implémenté | Moyenne | Possible | **P7**, P14 | `dry_run` par défaut ; confirmation | Journal | Confirmation stopgap | Test : kill sans confirmation refusé |
| **R-O26** | `file_controller` : racine autorisée = **tout `~`** (contient `.ssh`, `AppData`, le dépôt JARVIS lui-même et ses clés) ; écriture/écrasement sans confirmation ; suppression via corbeille (point positif) | Moyenne | Possible | P7 (décision), P13/P14 | Racines configurables restreintes (ADR-015, **proposé**) | Test de chemins | Restreindre aux dossiers utilisateur usuels | Test : accès à `~/.ssh` refusé |

## A.3 Autonomie, orchestration, contrats

| ID | Risque (preuve) | Gravité | Exposition | Phase | Prévention | Détection | Mitigation | Critère de vérification |
|---|---|---|---|---|---|---|---|---|
| **R-O09** | **Duplication et fiction de l'autonomie** : `core/autonomy_manager.py` = simulation (agents `SimpleTaskAgent`, `ExternalServiceAgent` → `api.example.com`), **aucun** `register_agent`/`submit_idea` dans le code applicatif ; `enabled` lu seulement dans du code mort ; `manage_autonomy` modifiable **par le modèle** ; coexiste avec `agent/task_queue.py` | Moyenne | Certaine | P5 (documentation honnête) → **P15** (moteur unique) | Un seul moteur ; niveaux d'autonomie ; fonction « expérimentale » étiquetée | Test d'architecture (une seule file) | V1 : étiqueter, retirer `basicConfig`, confirmation pour `enable` ; V1.5 : fusion | Test : `manage_autonomy(enable)` sans confirmation ⇒ refus (V1) ; une seule file (V1.5) |
| **R-O10** | **Deux dispatchers et deux déclarations d'outils** : `_execute_tool` (26) vs `_call_tool` (16) ; `core/tools.py` vs `PLANNER_PROMPT` ; paramètres divergents | Moyenne | Certaine | **P3** | Registre unique | Test `déclaration ⇔ handler` | Registre + dispatcher | 26/26 couverts ; instantané identique |
| **R-O11** | **Statut de tâche faux** : `TaskQueue._run_task` marque `COMPLETED` même si l'exécuteur renvoie un message d'abandon/échec ; tâche annulée en file jamais retirée ; aucun état persisté ; `_tasks` non borné | Haute | Certaine | **P5** | `ExecutionResult` typé | Tests | Statuts `FAILED/ABORTED/PARTIAL` | Tests de cycle de vie |
| **R-O12** | **Récupération d'erreurs incohérente** : `analyze_error(max_attempts=2)` force `REPLAN` dès la 2ᵉ tentative (3ᵉ jamais atteinte) ; `SKIP` = « réussi » ; `generate_fix` produit un `code_helper(run)` avec un paramètre `code` ignoré → renvoie une chaîne d'erreur **sans lever** ⇒ étape comptée réussie | Moyenne | Certaine | **P5** | Contrats d'étapes ; suppression de l'auto-fix par code | Tests | Aligner les compteurs ; `skipped` distinct ; replan seul | Tests du §P5 |
| **R-O27** | **Prompt / outils incohérents** : le prompt cite `memory_write` (outil inexistant : `save_memory`), des « commandes spéciales » sur des fichiers `USER_*.md` illisibles par le modèle, et « Don't ask for confirmation on simple tasks » | Moyenne | Certaine | P6, P7 | Test de cohérence prompt ↔ registre | Revue + test de recherche de noms d'outils | Corriger `core/prompt.txt` | Test : tout nom d'outil du prompt existe dans le registre |
| **R-O28** | `iot_control` = **simulation** (3 appareils fictifs en mémoire) déclarée comme outil réel (la description mentionne « simulation » côté `tools.py` mais l'outil peut être perçu comme réel) | Basse | Certaine | P14 | Étiquetage explicite | Revue | Description « simulé » ; refus d'affirmer un effet réel | Réponse de l'outil préfixée « [simulation] » |

## A.4 Fiabilité du temps réel et des threads

| ID | Risque (preuve) | Gravité | Exposition | Phase | Prévention | Détection | Mitigation | Critère de vérification |
|---|---|---|---|---|---|---|---|---|
| **R-O14** | **Concurrence et reconnexion** : `await _execute_tool` dans `_receive_audio` bloque la réception pendant les outils ; `hotkey_listener.start()` rappelé à chaque reconnexion (threads/raccourcis dupliqués) ; panne micro traitée comme transitoire ; pas de `session_resumption` ; `out_queue(maxsize=10)` avec `put_nowait` depuis le callback audio (`QueueFull` possible) | Moyenne | Probable | **P4** | Tâches détachées ; écouteur idempotent ; classification d'erreurs | Tests avec `FakeLiveSession` | Découper `jarvis_live` | Tests du §P4 |
| **R-O15** | **Partage d'écran** : le contexte UI est envoyé avec `turn_complete=True` à chaque cycle (1,5 s) → déclenche des tours de modèle (coût, latence, bruit vocal) | Moyenne | Probable | **P4** (après test opt-in), P16 | Envoi en contexte sans tour | Test d'intégration opt-in | `turn_complete=False` | Mesure du nombre de tours/min en partage |
| **R-O23** | Arrêt brutal : `shutdown_jarvis` → `os._exit(0)` après 1 s ; pas de fermeture des tâches, du tray, des écritures | Moyenne | Certaine | **P4** | Arrêt coopératif | Test d'arrêt | `application.shutdown()` + repli forcé journalisé | Aucun processus résiduel ; mémoire intacte |
| **R-O24** | `logging.basicConfig` exécuté à l'import de `core/autonomy_manager.py` ; `print` généralisé ; pas de niveaux ni de structure | Basse | Certaine | P5 (effet de bord), P13 | Configuration de logs unique | Revue | Retirer l'effet de bord ; événements structurés en V1.5 | Aucun `basicConfig` hors point d'entrée |

## A.5 Données, mémoire

| ID | Risque (preuve) | Gravité | Exposition | Phase | Prévention | Détection | Mitigation | Critère de vérification |
|---|---|---|---|---|---|---|---|---|
| **R-O13** | **Mémoire fragile** : lecture-modification-écriture non atomique (deux verrous séparés) ; JSON corrompu ⇒ mémoire vide silencieuse ⇒ prochain `save_memory` copie le fichier corrompu sur `.bak` (perte de la dernière bonne copie) ; élagage au-delà de 8 000 caractères signalé uniquement par un `print` console ; catégorie non validée dans l'outil du modèle ; contenu réinjecté dans le prompt (persistance d'injection) | **Haute** | Probable | **P6** (V1), P17 | Verrou englobant, quarantaine du corrompu, `.bak` seulement si valide, validation des catégories | Tests de charge et de corruption | Voir P6 | 50 écritures concurrentes sans perte ; corruption ⇒ `.bak` intact |

## A.6 Plateforme, qualité, légal

| ID | Risque (preuve) | Gravité | Exposition | Phase | Prévention | Détection | Mitigation | Critère de vérification |
|---|---|---|---|---|---|---|---|---|
| **R-O19** | **Promesse multi-OS non tenue** : README « Windows, macOS, Linux » ; ≥ 20 imports/usages Windows, 57 branchements `platform` ; `config/__init__.py` plante sans `api_keys.json` | Moyenne | Certaine | P9 (documentation), P14 (adaptateurs) | Support déclaré = Windows 10/11 | Revue README | Réécrire le README ; adaptateurs | Aucune promesse hors périmètre testé |
| **R-O21** | **Aucun test automatisé** (seul `test_live.py`, connexion réelle) | Haute | Certaine | **P1.0/P2** | Suite offline ; garde-réseau | CI | Voir P2 | `pytest -q` hors ligne vert |
| **R-O22** | **Licence contradictoire** : `LICENSE` = Apache-2.0 ; README = CC BY-NC 4.0 ; attribution « FatihMakes / MARK XXXIX » dans l'UI sans source de provenance claire | Moyenne | Certaine | P9 / ADR-019 | Décision explicite du propriétaire | Revue | Aligner README/LICENSE/UI ; vérifier la licence de toute base amont | Une seule licence affichée ; attribution conforme |

---

# PARTIE B — Risques futurs (liés à la refonte)

| ID | Risque | Gravité | Exposition | Phase | Prévention | Détection | Mitigation (proposée) | Critère de vérification |
|---|---|---|---|---|---|---|---|---|
| **R-F01** | **Élévation de privilèges par l'autonomie** : une tâche proactive contourne la permission (origine `autonomy`/`notification` traitée comme `user`) | **Critique** | Possible | P13, P15 | L'origine fait partie de la décision ; mêmes contrôles pour toutes les origines (ADR-007/008) | Journal des décisions ; test de matrice | Matrice niveau × risque × origine ; interdictions fondamentales intangibles | Matrice 4×4×3 verte ; aucune action ne contourne `check` |
| **R-F02** | **Boucle d'exécution infinie / dérive** du moteur autonome | Haute | Possible | P15 | Budgets obligatoires (temps, essais, replans, appels modèle) ; arrêt d'urgence | Compteurs d'événements ; alerte UI | Budgets non nuls par défaut ; arrêt en un geste | Test : budget épuisé ⇒ arrêt + rapport |
| **R-F03** | **Coût d'utilisation des modèles** (planification multiétape, `turn_complete` en boucle, embeddings distants) | Moyenne | Probable | P4, P11, P15 | Plafonds d'appels ; routage local quand permis ; mesure | Compteur d'appels par tâche | Plafonds configurables ; journalisation du volume | Rapport d'appels par tâche ; test de plafond |
| **R-F04** | **Régression lors de la migration des 26 outils** (contrats, paramètres, comportement) | Haute | Probable | P3, P14 | Instantané des déclarations ; tests de caractérisation ; vagues + adaptateurs enveloppants | Tests de contrat ; baseline S1-S11 | Un commit par outil ; retour arrière par tag | Instantané identique ; baseline verte |
| **R-F05** | **Contraintes matérielles** des moteurs locaux (RAM/GPU, temps de chargement, disque) | Moyenne | Probable | P11, P12 | Chargement à la demande ; contrôle RAM/GPU avant chargement ; extras optionnels | Mesure au premier usage ; avertissement | Modèles plus petits ; repli documenté | Mesures consignées ; message clair en cas d'insuffisance |
| **R-F06** | **Perte/corruption mémoire pendant la migration SQLite** (aller et retour) | Haute | Possible | P17 | Sauvegarde automatique avant `--apply` ; JSON source conservé ; `--dry-run` ; `integrity_check` | Test aller-retour ; vérification post-migration | `--rollback` | Migration réversible sur copie réelle |
| **R-F07** | **Latence audio et interruptions** dégradées (chaîne STT→LLM→TTS locale ; refactoring de `audio_io`) | Moyenne | Probable | P4, P12 | Mesures avant/après ; file bornée ; streaming | Métriques de latence (premier octet audio) | Mode intégré cloud conservé ; réglages de tampon | Mesures documentées vs baseline V1 |
| **R-F08** | **Fragilité de l'automatisation GUI** : faux succès (écran changé ≠ action réussie), mauvais destinataire, temporisations fixes | Haute | Probable | P16 | Vérification sémantique ; arbre d'accessibilité ; tentatives bornées ; statut `unverified` honnête | Tests `sidefx` W-1…W-5 | Préférer l'API/UIA aux coordonnées ; confirmer avant effet externe | Workflows de référence verts |
| **R-F09** | **Friction des confirmations** → l'utilisateur les désactive ou valide à l'aveugle (fatigue) | Moyenne | Probable | P13, P19 | Niveaux de risque calibrés ; aperçu clair ; regroupement | Taux de confirmation/refus journalisé | Réglage par outil/périmètre ; listes blanches explicites | Revue d'usage après 2 semaines |
| **R-F10** | **Fuite de données personnelles** vers un embeddeur ou provider distant (RAG, mémoire) | Haute | Possible | P11, P18 | Mode `local` par défaut ; consentement explicite par capacité ; pas d'envoi implicite | Test réseau bloqué ; journal des destinations | Refus si consentement absent | Test : aucune requête distante sans consentement |
| **R-F11** | **Empoisonnement de mémoire/RAG** : contenu indexé ou mémorisé contenant des instructions | Haute | Possible | P17, P18 | Provenance et étiquette `untrusted` pour tout passage récupéré ; les passages n'ont aucun pouvoir sur permissions/outils | Tests d'injection (documents piégés) | Encapsulation ; limite de taille ; revue des sources | Test : document piégé ne change ni permission ni outil |
| **R-F12** | **Dette de compatibilité plateforme** : faux sentiment de portabilité, adaptateurs jamais testés sur un autre OS | Moyenne | Possible | P14, V2 | Support déclaré = Windows ; contrats testés sur fake de plateforme | Revue de README | Pas de promesse multi-OS avant tests réels | Documentation exacte |
| **R-F13** | **Dérive de périmètre** : la V1 devient une réécriture simultanée (providers, RAG, autonomie) | Haute | **Probable** | toutes | Règle 6 du plan ; gates ; revue CTO à chaque phase | Écart entre diff et fiche de phase | Reporter en V1.5 ; ADR si changement | Chaque PR référence une phase et ses critères |
| **R-F14** | **Évolution/indisponibilité du fournisseur cloud** (versions d'API `v1alpha`/`v1beta`, modèles retirés, SDK hérité abandonné) | Moyenne | Probable | P10, P11 | Adaptateurs isolés ; configuration du nom de modèle ; tests d'intégration opt-in périodiques | Échecs `PROVIDER_UNAVAILABLE` ; test opt-in | Repli local/autre provider autorisé par politique | Changement de modèle sans modifier le code métier |
| **R-F15** | **Concurrence dans la nouvelle architecture** (moteur asynchrone, base de tâches, annulation) : deadlocks, états incohérents | Moyenne | Possible | P15 | Une seule boucle propriétaire ; transitions d'état centralisées ; `CancelToken` | Tests de stress ; assertions d'état | Machine à états explicite (APP_FLOW F-09) | Tests de concurrence verts |
| **R-F16** | **Capture accidentelle d'informations sensibles** par le nouveau pipeline (`perception/`) ou la rétention | Haute | Possible | P16 | Filtre universel ; aucune persistance d'image par défaut ; journal sans contenu | Revue de fichiers créés ; tests | Politique de rétention minimale ; masquage | Aucun fichier image créé par défaut |

---

# PARTIE C — Risques de processus et limites de l'audit

| ID | Risque | Gravité | Mitigation |
|---|---|---|---|
| **R-P01** | Aucune exécution n'a eu lieu pendant l'audit : certains comportements (latence, audio, comportement réel de `launch_persistent_context`, `session_resumption`, `v1alpha` vs `v1beta`) ne sont **pas vérifiés** | Moyenne | Baseline §0.4 de `DEVELOPMENT_PHASES.md` avant P0 ; tests d'intégration opt-in |
| **R-P02** | Modules non lus ligne à ligne : `flight_finder`, `game_updater`, `youtube_video`, `weather_report`, `file_processor` | Moyenne | Revue détaillée au début de P3 (inventaire d'outils) ; mise à jour de `PRD.md` §3.6 |
| **R-P03** | Contenu réel de `memory/long_term.json` et `memory/USER_*.md` (ignorés par Git) inconnu | Basse | Migration à blanc sur copie (P6, P17) |
| **R-P04** | Le propriétaire doit trancher plusieurs décisions (licence, purge d'historique, racines de fichiers) avant certaines phases | Moyenne | Marquées « proposé » dans `DECISIONS.md` ; bloquantes pour P0 (purge), P7 (racines), P9 (licence) |

---

## Synthèse (comptage)

| | Critique | Haute | Moyenne | Basse |
|---|---|---|---|---|
| Observés (28) | 2 (R-O01, R-O05) | 11 | 13 | 2 |
| Futurs (16) | 1 (R-F01) | 8 | 7 | 0 |

**Risques exigeant une action immédiate** : R-O01 (révoquer la clé) ; puis R-O05, R-O04, R-O07, R-O08 (P7) ; R-O13 avant toute modification de la mémoire réelle (sauvegarde).
