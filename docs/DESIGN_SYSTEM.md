# DESIGN_SYSTEM — Système visuel réel de JARVIS et plan de refonte

| | |
|---|---|
| **Document** | `DESIGN_SYSTEM.md` (9/9) |
| **Base** | `main` @ `2dbb971` — valeurs **relevées dans le code** (`ui/interface.py`, `ui/hud_canvas.py`, `ui/metrics.py`, `ui/components/metric_bar.py`, `ui/components/log_widget.py`, `ui/screen_overlay.py`, `ui/tray_indicator.py`) |
| **Statuts** | **[ACTUEL]** relevé dans le code · **[V1]** clarification sans refonte (P8) · **[CIBLE V1.5]** adaptation minimale (P19) |
| **Références** | `ADR-012` (préservation de l'identité), `ADR-021` (PyQt6/Tk), `APP_FLOW.md` (états), `DEVELOPMENT_PHASES.md` P8 et P19 |

> **Limite** : le rendu n'a pas été exécuté (audit statique, environnement Linux) ; aucune capture d'écran n'a été produite. Les valeurs ci-dessous sont celles du code. Les revues visuelles de P8/P19 se font sur Windows.

---

## 1. Direction artistique [ACTUEL]

**HUD « cyber-terminal » sombre** inspiré d'une interface d'assistant de science-fiction : fond bleu-noir quasi noir, **cyan électrique** comme couleur primaire, **orange** et **jaune ambre** comme accents d'activité/avertissement, **vert néon** pour l'écoute, **rouge-rose** pour la sourdine/les erreurs. Typographie **monospace** (Courier New) partout ; cadres fins à coins arrondis (≈ 4 px) ; un **canvas central animé** (anneaux rotatifs, balayage, particules, onde) dont le visage (`face.png`, optionnel) est entouré d'un halo.

Principes à préserver : (1) **sombre et dense** ; (2) **la couleur porte l'état** (cyan = neutre/info, vert = écoute, orange/ambre = travail, rouge = sourdine/erreur) ; (3) **monospace uniforme** ; (4) animation **continue mais discrète** (16 ms pour le HUD) ; (5) pas d'effets de verre/ombres portées.

---

## 2. Tokens de couleur [ACTUEL → V1]

Source relevée : `class C` de `ui/interface.py` et `ui/hud_canvas.py` (**identiques**, 21 tokens). `ui/components/metric_bar.py` en redéfinit 7, `ui/components/log_widget.py` 11 (**dont `BG` différent**).

| Token | Valeur | Rôle |
|---|---|---|
| `BG` | `#00060a` | fond de la fenêtre et du canvas HUD |
| `PANEL` | `#010d14` | fond des panneaux latéraux, en-tête, pied de page |
| `PANEL2` | `#010f18` | fond des cartes de métriques (`MetricBar`) |
| `BORDER` | `#0d3347` | bordures par défaut |
| `BORDER_B` | `#1a5c7a` | bordures « vives » (survol, séparateurs) |
| `BORDER_A` | `#0f4060` | bordures de composants (barres) |
| `PRI` | `#00d4ff` | couleur primaire (cyan) : titres, anneaux, texte IA |
| `PRI_DIM` | `#007a99` | primaire atténué : libellés secondaires |
| `PRI_GHO` | `#001f2e` | primaire « fantôme » : fonds actifs/survols |
| `ACC` | `#ff6b00` | accent orange : activité, `SPEAKING`, alerte moyenne |
| `ACC2` | `#ffcc00` | accent ambre : `THINKING`/`PROCESSING`, journal système |
| `GREEN` | `#00ff88` | vert néon : `LISTENING`, succès |
| `GREEN_D` | `#00aa55` | vert atténué |
| `RED` | `#ff3355` | rouge : erreurs, alerte critique des barres |
| `MUTED_C` | `#ff3366` | rouge-rose : micro coupé |
| `TEXT` | `#8ffcff` | texte principal |
| `TEXT_DIM` | `#3a8a9a` | texte atténué |
| `TEXT_MED` | `#5ab8cc` | texte intermédiaire |
| `WHITE` | `#d8f8ff` | blanc teinté : messages utilisateur |
| `DARK` | `#000d14` | fond très sombre (champs/zones) |
| `BAR_BG` | `#011520` | fond des rails de barres |

**Valeur inline hors palette** : barre `TMP` de `SysMetrics` = `#ff6688` (`MetricBar("TMP", "#ff6688")`).

### 2.1 Écarts de cohérence relevés (à traiter en P8 — **sans changer les valeurs affichées**, sauf cas notés)

| # | Écart | Preuve | Traitement V1 |
|---|---|---|---|
| E1 | **Quatre définitions** de la palette | `C` dans 4 fichiers | Un seul module `ui/theme.py` (tokens identiques) |
| E2 | `log_widget.C.BG = #010d14` (= `PANEL`) alors que `BG` ailleurs = `#00060a` | `ui/components/log_widget.py` | Introduire `LOG_BG = PANEL` (valeur conservée) ; plus de token `BG` homonyme |
| E3 | Couleurs hors palette : `#00BFFF` (marqueur/confirmation/tray), `white` (fond Tk), `#ff6688` | `ui/screen_overlay.py`, `ui/tray_indicator.py`, `ui/interface.py` | Tokens nommés `OVERLAY_ACCENT=#00BFFF`, `METRIC_TMP=#ff6688` (valeurs conservées) ; harmonisation éventuelle **décidée par le propriétaire** (le bouton « Confirmer » blanc sur `#00BFFF` a un contraste de **2,12:1**, sous le seuil AA) |
| E4 | États `ERROR` et `INITIALISING` rendus **en `PRI` par défaut** (branche `else` de `hud_canvas`) : l'**erreur n'est pas distinguée visuellement** | `ui/hud_canvas.py` l. 311-314 | `ERROR` → `RED` (**seul changement visuel intentionnel de la V1**, avec les deux nouveaux états du §6) |
| E5 | Classification des lignes de journal : `"err" in texte` capture « interpreter », « were »… | `ui/components/log_widget.py` l. 86 | Correspondance par mot entier / préfixe `ERR:` |

---

## 3. Typographie [ACTUEL]

| Usage | Police / taille / graisse (relevées) |
|---|---|
| Police unique | **Courier New** (monospace) |
| Titre « J.A.R.V.I.S » (en-tête) | 17 pt gras (relevé `QFont("Courier New", 17, Bold)`) |
| Badges d'en-tête, libellés de section | 7–9 pt, gras pour les sections |
| Statut HUD central (`● LISTENING`…) | **11 pt gras** |
| Valeurs de métriques | 9 pt gras ; libellés 7 pt gras |
| Journal d'activité | 8–9 pt |
| Champs de saisie | 9–10 pt |
| Titres de dialogue de configuration | 10–14 pt gras |
| Icônes emoji | `Segoe UI Emoji` 22 pt (une occurrence) ; `Arial` 22 pt (une occurrence) |
| Overlay Tk | `Segoe UI` 9 pt gras (boutons) |

**Observation** : les tailles vont de 6 à 22 pt, certaines très petites (6–7 pt). Aucune échelle typographique nommée n'existe (**à introduire en V1 sous forme de constantes**, valeurs conservées, voir §11).

---

## 4. Gabarit et responsive (desktop) [ACTUEL]

| Constante | Valeur | Fichier |
|---|---|---|
| Taille par défaut | **980 × 700** | `ui/interface.py` l. 45 |
| Taille minimale | **820 × 580** | l. 46 |
| Colonne gauche (monitor) | **148 px** fixe | l. 47 |
| Colonne droite (activité) | **340 px** fixe | l. 48 |
| En-tête | **54 px** | l. 573 |
| Pied de page | **22 px** | l. 787 |
| Fenêtre | centrée à l'écran au démarrage ; titre « J.A.R.V.I.S — MARK XXXIX » | l. 439-446 |
| Plein écran | `F11` (bascule) | l. 500-507 |

La colonne **centrale** (canvas HUD) absorbe le redimensionnement ; les colonnes latérales restent fixes (largeurs imposées par `setFixedWidth`). Aucun `QSplitter` n'est utilisé. Aucun support de haute densité de pixels (HiDPI) spécifique n'a été relevé (à vérifier sur Windows, V1).

---

## 5. Composants [ACTUEL]

### 5.1 En-tête (54 px)
Badge « MARK XXXIX » (`PRI_DIM`), titre « J.A.R.V.I.S » avec sous-titre « Just A Rather Very Intelligent System », **horloge** `hh:mm:ss` (14 pt gras, `PRI`, timer 1 s) et **date** alignées à droite. Fond `PANEL`.

### 5.2 Colonne gauche — « ◈ SYS MONITOR » (148 px)
Cinq `MetricBar` (hauteur **38 px**, largeur min. 80 px) : **CPU** (`PRI`), **MEM** (`ACC2`), **NET** (`GREEN`), **GPU** (`ACC`), **TMP** (`#ff6688`) ; en dessous `UP hh:mm` et `PROC n`, et l'OS. Collecte par `SysMetrics` (thread, timer UI 2 s). Valeurs absentes : `--`.

**`MetricBar`** : carte arrondie (rayon 4) fond `PANEL2`, bordure `BORDER_A`, rail `BAR_BG` (rayon 2), remplissage dans la couleur de la barre ; **seuils d'alerte** : > 65 % → `ACC` (orange), > 85 % → `RED` ; libellé 7 pt gras, valeur 9 pt gras.

### 5.3 Centre — `HudCanvas` (timer **16 ms**)
Éléments dessinés (relevés) : quadrillage 48 px ; 10 arcs de pulsation ; **3 anneaux rotatifs** (angles initiaux 0/120/240°, vitesses `[0.55, −0.35, 0.9]` au repos, `[1.3, −0.9, 2.0]` en parole) ; 2 arcs de **balayage** ; graduation tous les 10° ; **visage** (`face.png` optionnel, halo concentrique) ; **particules** (disque 2,5 px) ; **texte d'état** ; **onde à 36 barres** de 8 px.

### 5.4 Colonne droite (340 px)
- **ACTIVITY LOG** (`LogWidget`) : voir §8.
- **FILE UPLOAD** (`FileDropZone`, hauteur **120 px**) : glisser-déposer ; animation (timer 30 ms) ; catégories reconnues par extension — *image* (jpg, jpeg, png, gif, webp, bmp, svg), *document* (pdf, docx, txt, md, pptx), *code* (py, js, ts, html, css, java, cpp, go), *data* (csv, xlsx, json, xml). Le fichier déposé devient `current_file` (utilisé par défaut par `file_processor`).
- **COMMAND INPUT** : champ (hauteur **30 px**) + bouton d'envoi **30×30** ; Entrée envoie.
- **Bouton micro** (hauteur 30, 8 pt gras) : « 🎙  MICROPHONE ACTIVE » ↔ « 🔇  MICROPHONE MUTED » (fond `#140006`, texte `MUTED_C`) ; bascule par clic ou **F4**.
- **Bouton plein écran** (hauteur 26) : « ⛶ FULLSCREEN [F11] ».

### 5.5 Pied de page (22 px)
Raccourcis « [F4] Mute · [F11] Fullscreen » ; mention « FatihMakes Industries · MARK XXXIX · CLASSIFIED » et « © FATIHMAKES » (`PRI_DIM`) — **à aligner sur la décision de licence** (ADR-019).

### 5.6 Dialogue de configuration (`SetupOverlay`)
Carte **460 × 390** centrée, titre « Configure J.A.R.V.I.S. before first boot. » ; champ clé **masqué** (hauteur 32) ; trois boutons d'OS (Windows / macOS / Linux, hauteur 32, pré-sélection selon `platform.system()`) ; bouton d'initialisation (hauteur 36).
**[V1]** ajouts : ligne d'aide « La clé est enregistrée dans `.env` (fichier local non chiffré) » ; lien « Supprimer la clé » ; message d'erreur en `RED` sous le champ ; seul Windows est présenté comme **supporté** (macOS/Linux libellés « non supporté » — décision à valider par le propriétaire).

### 5.7 Icône de zone de notification (`TrayIndicator`)
Icône **64×64** (disque cyan `#00BFFF` évidé, fond noir) ; infobulle « JARVIS — Partage d'écran actif » ; menu unique « Arrêter le partage ». Rôle : **indicateur de confidentialité obligatoire** pendant le partage d'écran.

### 5.8 Overlay d'écran (`ScreenOverlay`, Tkinter)
- **Marqueur** : fenêtre sans bordure, fond blanc rendu transparent, cercle `#00BFFF` (épaisseur 3) + point central + libellé, durée configurable, centré sur la cible.
- **Confirmation** (`confirm_action`) : fenêtre **340 × 110** au-dessus du point, bouton « Confirmer » (fond `#00BFFF`, texte blanc, `Segoe UI` 9 gras), annulation à l'expiration. **Implémentée mais jamais appelée aujourd'hui.**
- Contrainte : un `tk.Tk()` éphémère par affichage, dans un thread (fragile ; ADR-021).

---

## 6. États visuels de JARVIS [ACTUEL → V1 → V1.5]

| État | Source | Rendu HUD (texte, couleur) | Statut |
|---|---|---|---|
| `INITIALISING` | défaut | `●/○ INITIALISING`, `PRI` (clignotement) | [ACTUEL] |
| `THINKING` | connexion, outil en cours | `◈/◇ THINKING`, `ACC2` | [ACTUEL] |
| `PROCESSING` | traitement | `▷/▶ PROCESSING`, `ACC2` | [ACTUEL] (peu utilisé) |
| `LISTENING` | prêt | `●/○ LISTENING`, `GREEN` | [ACTUEL] |
| `SPEAKING` | sortie audio | `● SPEAKING`, `ACC` ; anneaux plus rapides, particules, onde active | [ACTUEL] |
| `MUTED` | F4 | `⊘ MUTED`, `MUTED_C` ; onde plate | [ACTUEL] |
| `ERROR` | échec fatal | rendu **`PRI` par défaut (non distinct)** | [ACTUEL] — **E4** |
| `ERROR` (corrigé) | idem | `⚠ ERROR`, `RED` | [V1, P8] |
| `NOT_CONFIGURED` | clé absente | `○ NOT CONFIGURED`, `ACC2` + message « Ouvrez les paramètres » | [V1, P8] |
| `OFFLINE` | réseau/provider indisponible | `○ OFFLINE`, `ACC` + « Reconnexion… » | [V1, P8] |
| `AWAITING_CONFIRMATION` | confirmation demandée | `? CONFIRM`, `ACC2` (clignotement) | [CIBLE V1.5, P19] |
| `TASK_RUNNING` | tâche en arrière-plan | badge en en-tête, pas de remplacement du statut vocal | [CIBLE V1.5, P19] |

Règle : le statut vocal (écoute/parole/sourdine) et le statut **tâche/autonomie** sont **deux indications distinctes** ; la seconde n'écrase jamais la première.

---

## 7. Animations et fréquences [ACTUEL]

| Élément | Fréquence / paramètres |
|---|---|
| `HudCanvas` | `QTimer` **16 ms** ; vitesse des anneaux et de l'onde fonction de `speaking` ; clignotement de l'état à ~0,5 s (0,12 s en parole pour la mise à jour d'onde) |
| `FileDropZone` | `QTimer` 30 ms (animation de glisser) |
| Horloge d'en-tête | 1 s |
| Métriques | 2 s |
| `LogWidget` | effet **machine à écrire** : 6 ms par caractère, 20 ms entre lignes (`QTimer`) |

**Règle V1** : aucune nouvelle animation ; borner la file de saisie du `LogWidget` (accumulation possible lors de rafales). **Règle V1.5** : les nouveaux indicateurs (tâches, confirmation) utilisent des **états fixes** ou le clignotement existant, pas de nouvelle boucle d'animation.

---

## 8. Affichage des journaux [ACTUEL]

`LogWidget` (fond `PANEL`/`#010d14`, bordure `BORDER`) : une ligne = préfixe + texte ; **étiquettes** déduites du texte : `you` (préfixe « You: », `WHITE`), `ai` (préfixe « Jarvis: », `PRI`), `err` (contient « err », `RED`), `sys` (autre, `ACC2`). Défilement automatique vers le bas ; sélection de texte possible.

**V1** : détection d'erreur par préfixe/mot entier (E5) ; limite de lignes conservées (mémoire UI) ; aucune donnée sensible affichée (les secrets n'y sont jamais écrits — à vérifier par test).
**V1.5** : un second flux **« TASKS »** (panneau compact sous le journal) liste la tâche courante, l'étape, le statut (`ok/skipped/failed/unverified`) et le bouton **Stop** ; le journal reste textuel.

---

## 9. Erreurs, confirmations et permissions

### 9.1 Erreurs [ACTUEL → V1 → V1.5]
- **Actuel** : lignes `ERR:` en `RED` dans le journal + message vocal (« Sir, … encountered an error ») ; état HUD non distinct (E4).
- **V1** : `ERROR` en `RED` ; message d'erreur **compréhensible** (code d'erreur → texte utilisateur, `BACKEND_SCHEMA.md` §2.5) ; pas de stacktrace ; action de repli proposée (« Vérifier la clé », « Reconnexion en cours »).
- **V1.5** : erreur de reprise de tâche : ligne dans le panneau TASKS (`failed` en `RED`, `unverified` en `ACC2`) avec cause et prochaine étape (réessai/replanification/aide demandée).

### 9.2 Confirmations
- **Actuel** : fenêtre Tk 340×110 (non appelée).
- **V1 (stopgap)** : réutiliser ce dialogue **ou** une boîte Qt minimale aux couleurs du HUD ; contenu : verbe d'action, cible, aperçu ; boutons Confirmer/Annuler ; **expiration 30 s = refus**.
- **V1.5** : `ui/dialogs/confirm_dialog.py` (Qt) : titre = action ; corps = **résumé généré par le système** ; badge d'**origine** (`USER`/`AUTONOMY`/`NOTIFICATION`) ; niveau de risque par couleur existante (`MEDIUM`=`ACC2`, `HIGH`=`ACC`, `CRITICAL`=`RED`) ; bouton par défaut = **Annuler** ; aperçu pour les envois de messages.

### 9.3 Permissions et autonomie [CIBLE V1.5]
Badge d'en-tête **`AUTONOMY: OFF | ASSISTED | SUPERVISED | AUTONOMOUS`** (couleurs : `TEXT_DIM`, `PRI`, `ACC2`, `ACC`) ; bouton **STOP** (rouge `RED`) toujours visible quand une tâche tourne ; changement de niveau = dialogue de confirmation (jamais par le seul modèle).

---

## 10. Raccourcis et accessibilité [ACTUEL → V1.5]

| Élément | État actuel | Proposition |
|---|---|---|
| Raccourcis | **F4** mute, **F11** plein écran (`QShortcut`) ; **Entrée** envoie | V1.5 : **Échap** = Stop tâche ; **Ctrl+,** = paramètres (à valider) |
| Raccourci global | Ctrl+Shift+J « regarde ici » (`keyboard`) | inchangé (V1) ; filtre de confidentialité ajouté (P7) |
| Contraste (WCAG, calculé sur `BG #00060a` / `PANEL #010d14`) | `TEXT` 17,0 / 16,4 ; `TEXT_MED` 8,9 / 8,6 ; `TEXT_DIM` **5,1 / 4,9** ; `PRI` 11,5 ; **`PRI_DIM` 4,1 / 4,0** ; `ACC` 7,1 ; `ACC2` 13,5 ; `GREEN` 15,2 ; `RED` 5,7 ; `MUTED_C` 5,7 | `PRI_DIM` (**< 4,5:1**) ne doit pas porter de texte informatif ≤ 9 pt (libellés décoratifs seulement) ; `TEXT_DIM` à la limite (5:1) : ok pour texte secondaire |
| Tailles de police | 6–7 pt présentes | ne pas descendre sous 8 pt pour du texte informatif (nouveaux composants) |
| Navigation clavier / lecteurs d'écran | non évaluées (audit statique) | V1.5 : ordre de tabulation défini, `accessibleName` sur les boutons d'état ; **à vérifier par test manuel sous Windows** |
| Information par la couleur seule | l'état est aussi porté par un **symbole** (`●/○`, `⊘`, `◈`) | conserver cette redondance pour les nouveaux états |

---

## 11. Contraintes PyQt6 et architecture UI

| Contrainte | Détail |
|---|---|
| Thread | tout accès à un widget depuis le thread Qt ; le moteur émet des **signaux** (`_log_sig`, `_state_sig`) — comportement actuel à préserver (C-17) |
| `_RootShim` | `JarvisUI.root` imite l'API Tk (`mainloop`, `protocol`) pour `main.py` ; **conservé** (ADR-021) |
| Mélange Qt/Tk | `ScreenOverlay` (Tk) tourne dans des threads ; fragile ; remplacement évalué en P19 |
| Style | feuilles de style (`setStyleSheet`) composées en f-strings avec les tokens ; pas de fichier QSS ; **V1** : centraliser les gabarits de style récurrents dans `ui/theme.py` |
| Polices | Courier New / Segoe UI Emoji : **Windows** ; sur d'autres OS le rendu changera (hors périmètre V1) |
| Offscreen | tests UI avec `QT_QPA_PLATFORM=offscreen` (pytest-qt) |
| Dépendances | PyQt6 uniquement ; **aucun** composant web (pas de Qt WebEngine) |

---

## 12. Plan V1 (P8) — clarifier **sans redessiner**

1. **`ui/theme.py`** (futur) : `class Colors` (21 tokens du §2 **à valeurs identiques** + `LOG_BG`, `OVERLAY_ACCENT`, `METRIC_TMP`), `class Fonts` (constantes : `FAMILY="Courier New"`, tailles nommées `XS=7, S=8, M=9, L=10, TITLE=17, STATUS=11` — **valeurs relevées**), `class Metrics` (tailles du §4), `qcol(hex, alpha)` (aujourd'hui dupliquée), gabarits de style.
2. Remplacer les quatre `class C` par `from ui.theme import Colors as C` (alias pour limiter le diff).
3. Corriger E2, E4 (état `ERROR`), E5 ; ajouter `NOT_CONFIGURED` et `OFFLINE` (§6).
4. Dialogue de configuration (§5.6) ; message d'erreur.
5. `LogWidget` : file bornée.
6. **Ne pas** toucher : géométrie, animations, `HudCanvas` (hors états), `ScreenOverlay` (ADR-021).

**Critères de réussite (testables)** : test d'instantané des 21 tokens (valeurs identiques au §2) ; démarrage offscreen sans clé → `NOT_CONFIGURED` ; `ERROR` rendu en `RED` ; F4/F11 inchangés ; revue visuelle avant/après **identique** hors §6.

---

## 13. Adaptations minimales V1.5 (P19) — sans dégrader le HUD

| Besoin | Emplacement | Composant (futur) | Règle visuelle |
|---|---|---|---|
| Provider actif et mode (cloud/local/mixte) | **pied de page** (à gauche des raccourcis) | `ui/components/provider_badge.py` | texte 8 pt `TEXT_MED` ; point vert/orange/rouge (santé) |
| Paramètres des providers | dialogue modal | `ui/dialogs/provider_settings.py` | style de `SetupOverlay` ; clé masquée ; « Supprimer la clé » |
| Niveau d'autonomie | **en-tête**, à côté du titre | `ui/components/autonomy_badge.py` | couleurs du §9.3 ; clic = dialogue de changement |
| Progression des tâches | colonne droite, **entre journal et dépôt de fichier** | `ui/components/task_panel.py` | liste compacte ; statuts `ok/skipped/failed/unverified` ; bouton **STOP** |
| Demande de confirmation | dialogue modal centré | `ui/dialogs/confirm_dialog.py` | §9.2 |
| Récupération d'erreur | panneau TASKS + ligne de journal `ERR:` | — | §9.1 |
| Indicateur de capture écran | **tray** (existant) + pastille d'en-tête `CAPTURE` en `ACC` | `ui/components/capture_indicator.py` | visible tant que la capture est active |

Contraintes : la **colonne droite** reste à 340 px ; le panneau TASKS est **repliable** (masqué si aucune tâche) ; **aucune** modification de `HudCanvas` hors ajout d'états ; pas de nouvelle police ni de nouvelle couleur (réutilisation des 21 tokens).

**Critères** : revue visuelle HUD inchangé à l'état repos ; parcours critiques offscreen (configuration providers, confirmation, annulation, erreur) ; aucun texte informatif < 8 pt.

---

## 14. Hors périmètre

Interface web, remplacement de PyQt6, thème clair, refonte de l'identité, traduction de l'interface (l'UI est en anglais ; la **localisation** est une décision produit à prendre séparément), animation supplémentaire.
