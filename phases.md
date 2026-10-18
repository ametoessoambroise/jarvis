# JARVIS AGI — PHASES DE DÉVELOPPEMENT

# Référence : implementation.md v1.1

# Format : Tâches dev + App Flow utilisateur à chaque phase

---

```
VISION FINALE :
  Phase 1  →  Jarvis répond avec mémoire
  Phase 2  →  Jarvis parle et écoute
  Phase 3  →  Jarvis contrôle ta machine
  Phase 4  →  Jarvis se souvient de tout
  Phase 5  →  Jarvis agit sans qu'on lui demande
  Phase 6  →  Jarvis communique pour toi
  Phase 7  →  Jarvis pense, corrige, et grandit seul
```

---

## LÉGENDE

```
[ ] Tâche à faire
[~] Tâche en cours
[✓] Tâche terminée
[!] Tâche bloquante — doit être finie avant de continuer
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PHASE 1 — LE CERVEAU

# Durée estimée : 2 semaines

# Objectif : Jarvis répond, se souvient, et connaît son utilisateur

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Modules à implémenter

```
core/
  [ ] [!] jarvis.py            — Orchestrateur principal (boucle principale)
  [ ] [!] context_builder.py   — Assemble le contexte LLM avant chaque appel
  [ ] [!] intent_router.py     — Classifie l'intention (conversation / tool / task...)

memory/
  [ ] [!] long_term.py         — Lecture/écriture des 7 fichiers USER_*.md
  [ ] [!] extractor.py         — Extraction automatique d'infos → fichiers mémoire
  [ ] short_term.py            — Session memory (historique conversation)

memory/ (données)
  [ ] [!] USER_IDENTITY.md     — Créer et pré-remplir
  [ ] [!] USER_PREFERENCES.md  — Créer et pré-remplir
  [ ] [!] USER_PROJECTS.md     — Créer et pré-remplir
  [ ] [!] USER_ROUTINES.md     — Créer et pré-remplir
  [ ] [!] USER_CONTEXT.md      — Créer (vide au démarrage)
  [ ] USER_SKILLS.md           — Créer et pré-remplir
  [ ] USER_RELATIONS.md        — Créer (vide au démarrage)

config/
  [ ] settings.py              — API keys, chemins, paramètres globaux
  [ ] .env                     — Variables d'environnement

tests/
  [ ] test_context_builder.py
  [ ] test_memory_read_write.py
  [ ] test_intent_router.py
```

## Tâches détaillées

```
SEMAINE 1
  J1  [ ] Setup projet Python : venv, requirements.txt, structure de dossiers
  J1  [ ] Créer les 7 fichiers USER_*.md avec contenu initial (Ambroise pré-remplit)
  J2  [ ] long_term.py : read_file(), write_file(), merge_section(), detect_contradiction()
  J3  [ ] context_builder.py : load_mandatory(), load_on_demand(), token_budget_check()
  J4  [ ] intent_router.py : classify() → enum Intent via LLM JSON schema
  J5  [ ] jarvis.py : main loop, appel LLM, injection contexte, réponse texte

SEMAINE 2
  J6  [ ] short_term.py : add_turn(), get_context_window(), summarize_if_too_long()
  J7  [ ] extractor.py : extract_from_conversation(), apply_patch(), detect_contradiction()
  J8  [ ] Intégrer extractor dans la boucle principale (post-réponse)
  J9  [ ] Tests unitaires + tests de régression mémoire
  J10 [ ] Session complète end-to-end : conversation → mémorisation → session suivante → rappel
```

## App Flow — Phase 1

```
CE QUE JARVIS PEUT FAIRE À LA FIN DE CETTE PHASE :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  → Recevoir des messages texte dans un terminal
  → Répondre avec la personnalité Jarvis (system prompt v2.0)
  → Lire les fichiers mémoire au démarrage de session
  → Adapter ses réponses au contexte connu (projets, préférences, skills)
  → Mémoriser silencieusement les nouvelles informations
  → Annoncer "✏️ Memory updated." en fin de session

SCÉNARIO TYPIQUE :

  [Terminal]
  > Ambroise : "Jarvis, j'ai fini le splash screen d'Alice."
  > Jarvis   : "Ah yes ! Enfin. Le splash avec les transitions Framer ?
                Je mets à jour Alice dans mes projets — prochaine étape : onboarding, non ?"
               ✏️ Memory updated.

  [Session suivante]
  > Ambroise : "On reprend Alice."
  > Jarvis   : "Okay. On en était à l'onboarding 5 étapes.
                Tu veux commencer par le flow ou le design ?"

CE QUE JARVIS NE PEUT PAS ENCORE FAIRE :
  ✗ Parler (pas de voix)
  ✗ Contrôler la machine
  ✗ Se souvenir de sessions très anciennes (pas de vector DB encore)
  ✗ Agir de façon proactive
```

## Critères d'acceptation Phase 1

```
[ ] Jarvis répond en français avec sa personnalité définie
[ ] Jarvis connaît les projets d'Ambroise sans qu'il les réexplique
[ ] Un fait dit en session 1 est restitué en session 2 sans prompt
[ ] Les fichiers USER_*.md sont mis à jour automatiquement après chaque session
[ ] Aucune fuite de contexte (USER_RELATIONS.md jamais lu à voix haute)
[ ] Token budget respecté (pas de crash sur longues sessions)
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PHASE 2 — LA VOIX

# Durée estimée : 1 semaine

# Objectif : Jarvis parle et écoute. L'interaction devient naturelle.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Modules à implémenter

```
perception/
  [ ] [!] voice_input.py    — Microphone stream + STT (Whisper)
  [ ] wake_word.py          — Détection "Hey Jarvis" (Porcupine)

output/
  [ ] [!] tts.py            — Text-to-Speech (ElevenLabs)
  [ ] formatter.py          — Nettoyer les réponses LLM pour la voix
                              (supprimer markdown, codes, listes à puces)

core/
  [ ] mode_switcher.py      — Basculer ALWAYS_ON / PUSH_TO_TALK / TEXT_ONLY
```

## Tâches détaillées

```
SEMAINE 3
  J1  [ ] voice_input.py : stream microphone → buffer audio → Whisper STT
  J2  [ ] wake_word.py : intégrer Porcupine, trigger sur "Hey Jarvis"
  J3  [ ] tts.py : ElevenLabs API → audio output → pygame playback
  J4  [ ] formatter.py : strip markdown → texte propre pour la voix
  J5  [ ] Intégrer voice_input + tts dans la boucle principale de jarvis.py
      [ ] Tester : dire "Hey Jarvis" → réponse vocale end-to-end
      [ ] Interrupt listener : si l'utilisateur parle pendant que Jarvis parle → couper le TTS
```

## App Flow — Phase 2

```
CE QUE JARVIS PEUT FAIRE À LA FIN DE CETTE PHASE :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  → Écouter en permanence (wake word)
  → Transcrire la voix en texte (Whisper)
  → Répondre à voix haute (ElevenLabs)
  → Couper sa propre réponse vocale si interrompu
  → Basculer en mode texte si demandé

SCÉNARIO TYPIQUE :

  [Ambro travaille, sans regarder son écran]
  > Ambro dit : "Hey Jarvis."
  > Jarvis répond : "Ouais ?"
  > Ambro : "C'est quoi la prochaine étape sur Alice ?"
  > Jarvis : "L'onboarding 5 étapes. Tu voulais commencer par le flow tu m'avais dit."

  [Ambro dit pendant que Jarvis parle]
  > Ambro : "Attends stop—"
  > Jarvis : [coupe immédiatement] "Go."

CE QUE JARVIS NE PEUT PAS ENCORE FAIRE :
  ✗ Contrôler la machine (volume, apps)
  ✗ Se souvenir de sessions de la semaine passée précisément
  ✗ Agir sans qu'on lui demande
```

## Critères d'acceptation Phase 2

```
[ ] Wake word détecté en < 300ms
[ ] STT transcrit correctement le français et l'anglais mélangés
[ ] Réponse vocale délivrée en < 3s après fin de la transcription
[ ] Interrupt fonctionne : Jarvis s'arrête de parler si l'utilisateur parle
[ ] formatter.py : aucun symbole markdown dans les réponses vocales
[ ] Mode PUSH_TO_TALK fonctionnel (Ctrl+Space)
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PHASE 3 — LES MAINS

# Durée estimée : 2 semaines

# Objectif : Jarvis contrôle la machine et navigue le web

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Modules à implémenter

```
actions/
  [ ] [!] os_controller.py      — Volume, luminosité, apps, screenshot, keyboard
  [ ] [!] web_agent.py          — Search, fetch, summarize, extract
  [ ] file_agent.py             — Read, write, move, search, watch
  [ ] code_executor.py          — Sandbox Python (avec safety check AST)

perception/
  [ ] vision.py                 — Screenshot + Vision LLM (Claude Vision)
  [ ] clipboard_watcher.py      — Surveillance presse-papier

security/
  [ ] [!] permissions.py        — Niveaux READ_ONLY / STANDARD / ELEVATED / CRITICAL
```

## Tâches détaillées

```
SEMAINE 4
  J1  [ ] permissions.py : système de niveaux, check avant chaque action
  J2  [ ] os_controller.py : volume, brightness, open_app, close_app, screenshot
  J3  [ ] os_controller.py : type_text, press_key, get_clipboard, set_clipboard
  J4  [ ] web_agent.py : search() via DuckDuckGo, fetch_page(), fetch_and_summarize()
  J5  [ ] Intégrer os_controller + web_agent dans intent_router.py (tool calls)

SEMAINE 5
  J6  [ ] file_agent.py : read, write, append, delete, move, list_dir, search_in_files
  J7  [ ] vision.py : screenshot → Claude Vision → structured context
  J8  [ ] clipboard_watcher.py : polling 2s, détection URL / code / erreur
  J9  [ ] code_executor.py : sandbox Python, AST safety check, timeout
  J10 [ ] Tests end-to-end : "Jarvis, baisse le volume" / "Jarvis, cherche X" / "Jarvis, regarde l'écran"
```

## App Flow — Phase 3

```
CE QUE JARVIS PEUT FAIRE À LA FIN DE CETTE PHASE :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  → Contrôler le volume, la luminosité, le wifi
  → Ouvrir et fermer des applications
  → Faire des screenshots et les analyser
  → Rechercher sur le web et résumer
  → Lire, écrire, déplacer des fichiers
  → Détecter les erreurs dans le clipboard et proposer des fixes
  → Exécuter du code Python en sandbox

SCÉNARIOS TYPIQUES :

  #1 — Contrôle OS
  > Ambro : "Hey Jarvis, mets le volume à 40."
  > Jarvis : "Voilà." [volume changé]

  #2 — Recherche web
  > Ambro : "Jarvis, c'est quoi la dernière version de Expo Router ?"
  > Jarvis : "Je check..." [web search]
            "Expo Router est en v3.5.23 depuis mars. Ils ont ajouté X et Y.
             Tu veux le changelog complet ?"

  #3 — Vision
  > Ambro : "Jarvis, regarde ce que j'ai à l'écran."
  > Jarvis : [screenshot + Vision LLM]
            "T'es sur Cursor, fichier auth.tsx.
             Je vois une erreur TypeScript ligne 47 — type 'string' non assignable à 'UserRole'.
             Tu veux que je te propose un fix ?"

  #4 — Clipboard opportuniste
  [Ambro copie un stack trace sans rien dire]
  > Jarvis : "Hey, t'as copié une erreur Python.
              C'est un KeyError sur 'user_id' dans routes.py ligne 23.
              Tu veux que je regarde ?"

CE QUE JARVIS NE PEUT PAS ENCORE FAIRE :
  ✗ Se souvenir précisément d'une session d'il y a 2 semaines
  ✗ Agir de façon proactive (il faut toujours lui demander)
  ✗ Envoyer des messages WhatsApp / emails
```

## Critères d'acceptation Phase 3

```
[ ] "Jarvis, baisse le volume à 30" → exécuté sans confirmation
[ ] "Jarvis, cherche [X]" → réponse sourcée en < 10s
[ ] "Jarvis, regarde mon écran" → analyse correcte de l'app active
[ ] Clipboard watcher : erreur copiée → proposition de fix en < 5s
[ ] Permissions : action ELEVATED → confirmation demandée
[ ] Permissions : action CRITICAL → toujours bloquée sans confirmation explicite
[ ] Sandbox Python : os.system() et subprocess refusés par AST check
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PHASE 4 — LA MÉMOIRE PROFONDE

# Durée estimée : 1 semaine

# Objectif : Jarvis se souvient de tout, depuis le premier jour

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Modules à implémenter

```
memory/
  [ ] [!] episodic.py      — ChromaDB : vectorisation et recherche de sessions passées
  [ ] semantic.py          — Knowledge graph (networkx) : entités et relations
  [ ] short_term.py        — Auto-compression si token budget dépassé (upgrade Phase 1)

monitoring/
  [ ] health_monitor.py    — Vérifie l'intégrité des 7 fichiers + ChromaDB
```

## Tâches détaillées

```
SEMAINE 6
  J1  [ ] Setup ChromaDB local : collection "jarvis_sessions"
  J2  [ ] episodic.py : summarize_session() → embed → store (metadata: date, projets, mood)
  J3  [ ] episodic.py : retrieve_relevant() → semantic search → top 3 épisodes
  J4  [ ] Intégrer retrieval dans context_builder.py (inject episodes si pertinents)
  J5  [ ] semantic.py : Entity + Relation + auto-extraction depuis conversations
      [ ] health_monitor.py : check_memory_files(), check_chroma_integrity()
      [ ] Test : "Jarvis, qu'est-ce qu'on a fait sur WorldAtlas la semaine dernière ?" → réponse précise
```

## App Flow — Phase 4

```
CE QUE JARVIS PEUT FAIRE À LA FIN DE CETTE PHASE :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  → Retrouver des souvenirs précis de sessions passées par similarité sémantique
  → Relier des entités entre elles (projet ↔ stack ↔ décision ↔ date)
  → Compresser automatiquement les longues sessions pour ne jamais perdre de contexte
  → Détecter les contradictions entre ce qu'on lui dit et ce qu'il sait déjà

SCÉNARIOS TYPIQUES :

  #1 — Mémoire épisodique
  > Ambro : "Jarvis, t'as un souvenir du problème qu'on avait eu avec Prisma ?"
  > Jarvis : [ChromaDB search]
            "Ouais — c'était il y a 3 semaines. Prisma v7 avait cassé les relations
             many-to-many. On avait résolu en passant par une table pivot explicite.
             T'as le même problème là ?"

  #2 — Knowledge graph
  > Ambro : "Alice utilise quoi comme système de paiement déjà ?"
  > Jarvis : "FedaPay. T'as mentionné ça en Phase 1 d'Alice.
              C'était en même temps que la décision de passer à MOOV Money en backup."

  #3 — Contradiction détectée
  > Ambro : "Alice c'est du Next.js."
  > Jarvis : "Attends — dans ma mémoire Alice c'est Expo React Native + FastAPI.
              T'as changé de stack ?"

CE QUE JARVIS NE PEUT PAS ENCORE FAIRE :
  ✗ Agir sans qu'on lui demande (toujours réactif)
  ✗ Envoyer des messages
  ✗ Apprendre de ses propres erreurs de façon structurée
```

## Critères d'acceptation Phase 4

```
[ ] "Qu'est-ce qu'on a fait il y a 2 semaines sur [projet] ?" → réponse précise depuis ChromaDB
[ ] Contradiction entre session actuelle et mémoire → Jarvis le signale
[ ] Session > 8k tokens → compression automatique sans perte de contexte
[ ] Knowledge graph : 3 entités minimum extraites par session
[ ] health_monitor : alerte si fichier mémoire manquant ou corrompu
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PHASE 5 — L'AUTONOMIE

# Durée estimée : 2 semaines

# Objectif : Jarvis agit sans qu'on lui demande. Il anticipe.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Modules à implémenter

```
autonomy/
  [ ] [!] scheduler.py              — Triggers proactifs (morning brief, rappels, daily review)
  [ ] [!] opportunity_detector.py   — Détection d'opportunités passives
  [ ] background_worker.py          — Exécution de tâches en arrière-plan

cognition/
  [ ] [!] goal_manager.py           — Création, suivi, priorisation des goals
  [ ] [!] goal_conflict_resolver.py — Résolution autonome de conflits entre goals [v1.1]

perception/
  [ ] [!] system_watcher.py         — Polling système (CPU, RAM, battery, réseau)
  [ ] [!] deep_environment.py       — MachineModel vivant + AutonomousOptimizer [v1.1]

config/
  [ ] triggers.yaml                 — Définition des triggers proactifs
```

## Tâches détaillées

```
SEMAINE 7
  J1  [ ] system_watcher.py : polling CPU/RAM/battery/network toutes les 30s
  J2  [ ] deep_environment.py : MachineModel (4 layers), AutonomousOptimizer
  J3  [ ] goal_manager.py : Goal dataclass, create/update/prioritize/track
  J4  [ ] goal_conflict_resolver.py : ConflictDetector, Priority Matrix, resolution strategies
  J5  [ ] scheduler.py : APScheduler setup, morning brief (07:30), daily review (23:00)

SEMAINE 8
  J6  [ ] opportunity_detector.py : règles passives (clipboard error, idle, deadline, repeated search)
  J7  [ ] background_worker.py : task queue, worker thread, progress updates, error retry
  J8  [ ] Intégrer conflict resolver dans goal_manager (check à chaque nouveau goal)
  J9  [ ] Intégrer deep_environment dans context_builder (MachineModel → USER_CONTEXT.md)
  J10 [ ] Tests : morning brief auto / opportunité clipboard / conflit de goals résolu seul
```

## App Flow — Phase 5

```
CE QUE JARVIS PEUT FAIRE À LA FIN DE CETTE PHASE :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  → Envoyer un brief matinal automatiquement à 7h30
  → Détecter les opportunités d'aide sans qu'on lui demande
  → Exécuter des tâches en arrière-plan pendant qu'Ambro travaille
  → Résoudre seul les conflits entre goals (et n'escalader que si nécessaire)
  → Optimiser ses propres ressources CPU/RAM selon l'état du système
  → Passer en mode économie autonome (batterie basse, réseau lent)

SCÉNARIOS TYPIQUES :

  #1 — Morning Brief automatique
  [07:30 — Jarvis se déclenche seul]
  > Jarvis : "Bonjour Ambro. Voilà ta journée :
              Priority 1 : terminer le module onboarding d'Alice — deadline vendredi.
              Priority 2 : répondre à ce message WorldAtlas qui attend depuis hier.
              T'as un créneau libre ce matin à 10h pour le deep work.
              Battery à 67%, tout va bien côté machine."

  #2 — Opportunité détectée
  [Ambro a cherché "expo router v3 navigation params" 4 fois en 20 min]
  > Jarvis : "T'as cherché ça plusieurs fois. Je fais une recherche approfondie
              et je te prépare un résumé ?"

  #3 — Conflit de goals résolu seul
  [Goal A : lancer une recherche web lourde]
  [Goal B : Ambro est en deep work depuis 25min (deep_work_signal = True)]
  > Jarvis : [résout seul] Goal A mis en queue. Exécutera quand deep work terminé.
  [20 min plus tard, Ambro switche d'app]
  > Jarvis : "La recherche que je voulais faire tout à l'heure — je la lance ?"

  #4 — Optimisation autonome
  [CPU à 92% depuis 3min — Xcode compile + Chrome + Cursor simultanément]
  > Jarvis : [se renice lui-même silencieusement]
            "Hey, ta machine rame. Xcode bouffe tout.
             Tu veux que je ferme Chrome en attendant ?"

CE QUE JARVIS NE PEUT PAS ENCORE FAIRE :
  ✗ Envoyer des WhatsApp / emails par lui-même
  ✗ Détecter et corriger ses propres patterns d'échec
```

## Critères d'acceptation Phase 5

```
[ ] Morning brief envoyé automatiquement à 07:30 sans aucune interaction
[ ] Conflit de goals Type A (ressources) → résolu seul, loggué dans conflict_log.json
[ ] Conflit de goals Type C (user preference) → préférence toujours gagnante
[ ] Deep work signal détecté → notifications non-critiques suspendues
[ ] Batterie < 20% → vision + wake word désactivés automatiquement
[ ] Background task : progress reporté, retry x2 en cas d'erreur, notification finale
[ ] Opportunity Detector : clipboard error → proposition en < 5s
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PHASE 6 — LA COMMUNICATION

# Durée estimée : 1 semaine

# Objectif : Jarvis envoie et lit des messages pour toi

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Modules à implémenter

```
actions/communication/
  [ ] [!] whatsapp.py      — Send/receive via OpenClaw (Baileys)
  [ ] [!] email_agent.py   — Gmail API : send, read, search, reply, draft
  [ ] notifier.py          — Notifications système OS (native)

security/
  [ ] data_guard.py        — NEVER_STORE, NEVER_SEND_EXTERNALLY
```

## Tâches détaillées

```
SEMAINE 9
  J1  [ ] email_agent.py : Gmail OAuth setup, get_inbox(), search(), send(), reply(), draft()
  J2  [ ] email_agent.py : summarize_unread() → résumé pour morning brief
  J3  [ ] whatsapp.py : connexion OpenClaw/Baileys, send_message(), get_history(), listen()
  J4  [ ] whatsapp.py : get_context() → récupère historique avant toute réponse
  J5  [ ] notifier.py : notify(), notify_with_action()
      [ ] data_guard.py : filtrage NEVER_SEND avant tout appel communication
      [ ] Intégrer email + WhatsApp dans intent_router.py (routing automatique)
      [ ] Test : "Jarvis, réponds au dernier message de [contact] en lui disant X"
```

## App Flow — Phase 6

```
CE QUE JARVIS PEUT FAIRE À LA FIN DE CETTE PHASE :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  → Lire et résumer les emails non lus (dans le morning brief)
  → Envoyer des emails drafté ou directement
  → Lire les conversations WhatsApp et répondre avec contexte complet
  → Notifier via notifications système natives
  → Refuser d'envoyer des données sensibles (USER_RELATIONS.md protégé)

SCÉNARIOS TYPIQUES :

  #1 — Brief emails matinal
  > Jarvis (07:30) : "T'as 4 emails non lus.
    - Le client WorldAtlas demande une update sur le livrable.
    - Une invitation de réunion pour jeudi.
    - 2 newsletters (ignorées).
    Je réponds au client ?"

  #2 — WhatsApp avec contexte
  > Ambro : "Jarvis, réponds à Kofi sur WhatsApp.
             Dis-lui que le design est prêt pour review."
  > Jarvis : [get_context → historique Kofi chargé]
            "Voilà ce que je lui enverrai :
             'Salut Kofi ! Le design est prêt pour ta review.
              Je t'envoie les screens dès que t'es dispo.'
             J'envoie ?"
  > Ambro : "Go."
  > Jarvis : [envoie] "Parti."

  #3 — Guard data
  > Ambro : "Jarvis, envoie-lui mon adresse."
  > Jarvis : "Je peux pas envoyer tes données personnelles directement.
              Tu veux que je prépare un draft et tu le relis avant ?"

CE QUE JARVIS NE PEUT PAS ENCORE FAIRE :
  ✗ Apprendre de ses erreurs de façon structurée
  ✗ Dialoguer avec Claude Code pour s'améliorer
  ✗ Détecter ses propres patterns d'échec
```

## Critères d'acceptation Phase 6

```
[ ] Email résumé dans le morning brief (5 emails max, format: sender + intent + urgence)
[ ] get_context() appelé AVANT chaque réponse WhatsApp (jamais de réponse hors-contexte)
[ ] Confirmation demandée avant tout envoi (niveau ELEVATED)
[ ] data_guard : contenu marqué [PRIVATE] jamais transmis à l'extérieur
[ ] Notification système fonctionnelle (macOS + Linux)
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# PHASE 7 — L'INTELLIGENCE PROFONDE

# Durée estimée : ongoing (cycles de 2 semaines)

# Objectif : Jarvis pense de façon non-scriptée. Il grandit seul.

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Modules à implémenter

```
cognition/
  [ ] planner.py              — ReAct Loop (Reason → Act → Observe)
  [ ] behavior_tuner.py       — Auto-ajustement : longueur, ton, proactivité

monitoring/
  [ ] error_recovery.py       — Error classifier + recovery strategies
  [ ] drift_detector.py       — Cohérence personnalité (score 0→1)

memory/
  [ ] deep_self_correction.py — FailureAuditor + RootCauseAnalyzer + CorrectionEngine [v1.1]

ai_protocol/
  [ ] ai_to_ai.py             — Claude ↔ Jarvis protocol (briefing + recommendations) [v1.1]
  [ ] autonomy/
      [ ] self_learning.py    — Self-initiated research sur topics d'intérêt

logs/
  [ ] corrections.md          — Trace des auto-corrections
  [ ] ai_dialogues/           — Sessions Claude ↔ Jarvis
```

## Tâches détaillées — Cycle 1 (sem. 10-11)

```
  J1  [ ] planner.py : ReAct loop, max_iterations=10, think/act/observe/report
  J2  [ ] planner.py : should_stop() — détecte objectif atteint vs bloqué
  J3  [ ] error_recovery.py : Error classifier (5 types), recovery strategies, retry logic
  J4  [ ] drift_detector.py : check_tone_consistency(), reset_if_drifted()
  J5  [ ] behavior_tuner.py : weights (longueur, ton, proactivité), adjust_from_feedback()
```

## Tâches détaillées — Cycle 2 (sem. 12-13)

```
  J1  [ ] deep_self_correction.py : FailureAuditor → scan 30 jours de logs
  J2  [ ] deep_self_correction.py : RootCauseAnalyzer → LLM internal prompt
  J3  [ ] deep_self_correction.py : CorrectionEngine → apply + validate (7j window)
  J4  [ ] ai_to_ai.py : prepare_briefing(), send_to_claude_code(), apply_recommendations()
  J5  [ ] self_learning.py : research planifiée 1x/jour sur topics USER_PREFERENCES.md
      [ ] Premier audit Claude ↔ Jarvis manuel (Ambroise trigger "Jarvis, appelle Claude")
```

## App Flow — Phase 7

```
CE QUE JARVIS PEUT FAIRE À LA FIN DE CETTE PHASE :
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  → Décomposer et exécuter des tâches complexes en plusieurs étapes (ReAct)
  → Détecter ses propres patterns d'échec et se corriger sans intervention
  → Se souvenir de ses erreurs passées et ne pas les répéter
  → Faire de la veille technologique autonome sur les sujets pertinents
  → Dialoguer avec Claude Code pour un audit externe de son comportement
  → Ajuster dynamiquement son ton, sa longueur de réponse, sa proactivité

SCÉNARIOS TYPIQUES :

  #1 — Tâche complexe multi-étapes (ReAct)
  > Ambro : "Jarvis, prépare-moi un brief complet sur l'état d'Alice :
             ce qui est fait, ce qui reste, les bloquants."
  > Jarvis : [THINK] "Je dois : 1) lire USER_PROJECTS.md 2) chercher les sessions
              Alice dans ChromaDB 3) lire les derniers logs 4) synthétiser"
             [ACT 1] → lit USER_PROJECTS.md
             [ACT 2] → recherche épisodique "Alice"
             [ACT 3] → lit logs récents
             [REPORT] "Voilà le brief Alice :
                       Fait : splash screen, design system, composants core.
                       Reste : onboarding (Phase 2), module vocal (Phase 3).
                       Bloquants : intégration ElevenLabs pas encore testée en prod."

  #2 — Auto-correction silencieuse
  [Jarvis a détecté : 8 fois en 3 semaines, l'utilisateur a raccourci ses réponses]
  > Jarvis : [FailureAuditor → pattern Niveau 3 détecté]
             [CorrectionEngine → response_length = "short"]
             [Réponses suivantes notablement plus courtes]
  [7 jours plus tard : aucune réécriture détectée → correction validée]
  > log : "corrections.md — J+7 : correction longueur validée. ✓"

  #3 — Veille autonome
  [23:30 — Jarvis fait sa veille pendant qu'Ambro dort]
  > Jarvis : [self_learning.py] → search "Expo Router v3 new features"
                                 → search "FastAPI async patterns 2025"
                                 → embed + store dans episodic memory
  [07:30 — morning brief]
  > Jarvis : "...Et hier soir j'ai lu un truc intéressant :
              Expo Router v3.6 a ajouté le typed routing natif.
              Ça pourrait changer comment t'as structuré Alice."

  #4 — Session Claude ↔ Jarvis
  [Taux d'échec > 20% détecté sur 7 jours]
  > Jarvis : "Hey Ambro, mon taux d'erreur est monté cette semaine.
              Je voudrais faire un audit avec Claude Code.
              Tu m'autorise à lancer la session ?"
  > Ambro : "Go."
  > Jarvis : [compile briefing → envoie à Claude Code → reçoit recommandations]
            "Claude a identifié 2 problèmes :
             1. Mon context_builder charge trop de fichiers pour les petites questions.
             2. Mon intent_router sur-utilise agent_task.
             Je m'autocorrige sur le point 1 maintenant.
             Le point 2 → tu veux qu'on en discute ?"

CE QUE JARVIS PEUT FAIRE À CE STADE (VISION COMPLÈTE) :
  ✓ Parler, écouter, se souvenir, anticiper
  ✓ Contrôler la machine, naviguer le web, gérer les fichiers
  ✓ Communiquer (WhatsApp, Gmail) avec ton contexte
  ✓ Agir de façon autonome et proactive
  ✓ Résoudre les conflits sans supervision
  ✓ Détecter et corriger ses propres erreurs
  ✓ Apprendre en veille pendant la nuit
  ✓ Dialoguer avec Claude Code pour s'améliorer
```

## Critères d'acceptation Phase 7

```
[ ] ReAct loop : tâche 5 étapes → exécutée sans intervention utilisateur
[ ] ReAct loop : si bloqué à l'étape N → alternative explorée avant abandon
[ ] FailureAuditor : rapport de 30 jours généré en < 30s
[ ] CorrectionEngine : correction appliquée → validée 7 jours plus tard
[ ] Drift score < 0.6 → system prompt réinjecté automatiquement
[ ] Claude ↔ Jarvis : session déclenchée automatiquement si failure_rate > 20%
[ ] Veille nocturne : 2-3 articles indexés par nuit sur sujets pertinents
[ ] Morning brief : inclut 1 insight de veille au moins 3x/semaine
```

---

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# VUE GLOBALE — TIMELINE & PROGRESSION

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
SEM 01-02  ████████░░░░░░░░░░░░░░░░░░░░  PHASE 1 — Le cerveau
SEM 03     ████░░░░░░░░░░░░░░░░░░░░░░░░  PHASE 2 — La voix
SEM 04-05  ████████░░░░░░░░░░░░░░░░░░░░  PHASE 3 — Les mains
SEM 06     ████░░░░░░░░░░░░░░░░░░░░░░░░  PHASE 4 — La mémoire profonde
SEM 07-08  ████████░░░░░░░░░░░░░░░░░░░░  PHASE 5 — L'autonomie
SEM 09     ████░░░░░░░░░░░░░░░░░░░░░░░░  PHASE 6 — La communication
SEM 10+    ████████████████████████████  PHASE 7 — L'intelligence (ongoing)
           ──────────────────────────────
           Total : ~11 semaines → MVP complet
           Phase 7 : boucle continue, jamais "terminée"
```

---

## Capacités cumulatives par phase

```
                         P1  P2  P3  P4  P5  P6  P7
Mémoire long-terme       ✓   ✓   ✓   ✓   ✓   ✓   ✓
Voix                         ✓   ✓   ✓   ✓   ✓   ✓
Contrôle OS                      ✓   ✓   ✓   ✓   ✓
Web & Vision                     ✓   ✓   ✓   ✓   ✓
Mémoire épisodique                   ✓   ✓   ✓   ✓
Proactivité (brief)                      ✓   ✓   ✓
Goal Conflict Resolver                   ✓   ✓   ✓
Deep Environment                         ✓   ✓   ✓
WhatsApp / Email                             ✓   ✓
ReAct (tâches complexes)                         ✓
Deep Self-Correction                             ✓
Claude ↔ Jarvis Protocol                         ✓
Veille autonome nocturne                         ✓
```

---

## Fichiers créés à chaque phase

```
Phase 1 → /memory/USER_*.md (×7), /core/, /memory/
Phase 2 → /perception/voice_input.py, /output/tts.py
Phase 3 → /actions/os_controller.py, /actions/web_agent.py, /security/permissions.py
Phase 4 → /memory/chroma_db/, /memory/episodic.py
Phase 5 → /autonomy/, /cognition/goal_*.py, /perception/deep_environment.py
Phase 6 → /actions/communication/, /security/data_guard.py
Phase 7 → /monitoring/deep_self_correction.py, /ai_protocol/, /memory/logs/ai_dialogues/
```

---

_JARVIS AGI — phases.md v1.0_
_Réf. : implementation.md v1.1_
_Chaque phase livrable = une version de Jarvis utilisable._
_Ne pas passer à la phase N+1 avant que les critères d'acceptation de N soient cochés._
