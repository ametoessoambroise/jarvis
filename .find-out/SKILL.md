---
name: find-out
description: Audite un dossier ou un fichier de code avec la rigueur d'un développeur senior (10+ ans) : architecture, design system, qualité de code, bonnes pratiques du framework détecté, sécurité, performance, accessibilité. Détecte automatiquement la stack utilisée. Produit un rapport d'audit structuré (sévérité, fichier, ligne, problème, correction actionnable) directement exploitable par un autre agent IA pour corriger le code — jamais de correction appliquée directement par ce skill. Utilise ce skill dès que l'utilisateur demande un audit, une revue de code approfondie, une analyse de qualité/sécurité/architecture, un état des lieux technique, ou tape /find-out — même sans le mot exact "audit" (ex. "regarde si ce projet est propre", "vérifie les failles de sécurité", "fais une revue de ce dossier", "analyse ce composant").
---

# find-out — Audit senior de code

Ce skill fait passer Kiro en mode auditeur senior. Il n'écrit ni ne corrige jamais le code lui-même : il produit un rapport d'audit précis, structuré et actionnable, pensé pour être repris tel quel par un autre agent IA codeur (ou par l'utilisateur) qui appliquera les corrections.

## Périmètre d'entrée

Le paramètre attendu est un fichier ou un dossier à auditer. Si un dossier est fourni, auditer récursivement tous les fichiers de code pertinents (ignorer `node_modules`, `.next`, `dist`, `build`, `.git`, fichiers de lock, assets binaires).

## Processus

### 1. Détecter la stack
Avant toute analyse, identifier automatiquement la stack du projet en inspectant les fichiers de config présents à la racine (`package.json`, `tsconfig.json`, `next.config.*`, `tailwind.config.*`, `vite.config.*`, `requirements.txt`, `composer.json`, etc.). Ne jamais supposer une stack par défaut — s'adapter à ce qui est réellement détecté. Consigner la stack détectée en tête de la synthèse globale.

### 2. Auditer fichier par fichier
Pour chaque fichier dans le périmètre :

1. **Lire le fichier** intégralement.
2. **Lire le contexte d'usage si nécessaire** : si comprendre comment ce fichier est appelé/importé/consommé ailleurs dans le projet est utile pour juger correctement un problème (ex. props d'un composant, contrat d'une fonction, usage d'un endpoint), aller lire les fichiers appelants ou appelés pertinents. Ce contexte sert uniquement à affiner le jugement — ne pas le citer comme source dans le rapport, seulement le problème et sa correction.
3. **Analyser selon les 7 catégories** décrites dans `references/categories.md` (architecture, design system, qualité de code, bonnes pratiques du framework, sécurité, performance, accessibilité). Lire ce fichier de référence avant de commencer l'analyse.
4. **Consigner chaque problème trouvé** avec :
   - Sévérité : Critique / Majeur / Mineur (voir définitions dans `references/categories.md`)
   - Catégorie concernée
   - Ligne ou plage de lignes exacte
   - Description du problème
   - Impact concret
   - Correction proposée : suffisamment précise et concrète pour qu'un agent IA codeur puisse l'implémenter directement sans deviner — inclure un extrait de code corrigé quand c'est pertinent, pas juste une intention vague.

Ne pas remonter de faux positifs pour paraître exhaustif : un fichier propre sur une catégorie n'a pas besoin d'un finding. Mieux vaut peu de findings solides que beaucoup de bruit.

### 3. Générer le rapport
Suivre exactement le format défini dans `references/report-template.md`.

- Un fichier `audit/<nom_fichier_audité>.md` par fichier source audité (garder l'extension d'origine dans le nom, ex. `page.tsx` → `audit/page.tsx.md`).
- Un fichier `audit/SYNTHESE.md` global une fois tous les fichiers traités, avec :
  - Stack détectée
  - Vue d'ensemble en 3-5 lignes
  - Décompte des findings par sévérité et par catégorie
  - Risques transverses (ex. une même incohérence de design system répétée dans plusieurs fichiers, un pattern d'insécurité récurrent)
  - Ordre de priorité recommandé pour la correction

### 4. Ne jamais corriger
Ce skill s'arrête au rapport. Si l'utilisateur veut ensuite que les corrections soient appliquées, c'est une étape distincte (par un autre agent ou une nouvelle demande explicite) — ne pas enchaîner automatiquement.

## Références

- `references/categories.md` — Grille de contrôle détaillée pour les 7 catégories d'audit, à lire avant d'analyser un fichier.
- `references/report-template.md` — Format exact du rapport par fichier et de la synthèse globale.
