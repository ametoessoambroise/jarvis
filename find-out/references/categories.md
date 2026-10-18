# Grille de contrôle — 7 catégories d'audit

Lire ce fichier avant d'analyser un fichier source. Adapter les points ci-dessous à la stack réellement détectée (ne pas appliquer des règles Next.js à un projet Vue, par exemple).

## Définition des sévérités

- **Critique** : faille de sécurité exploitable, bug bloquant en production, risque de perte/fuite de données, crash garanti dans un cas d'usage normal.
- **Majeur** : impact significatif et probable sur la maintenabilité, la performance, l'UX ou la fiabilité, même sans être bloquant immédiatement.
- **Mineur** : style, incohérence légère, dette technique faible, amélioration facultative.

## 1. Architecture / structure du projet

- Séparation des responsabilités (logique métier vs UI vs accès données)
- Organisation des dossiers cohérente avec les conventions du framework détecté
- Couplage excessif entre modules qui devraient être indépendants
- Duplication de logique qui devrait être mutualisée
- Conventions de nommage cohérentes dans tout le projet
- Gestion des dépendances circulaires

## 2. Cohérence du design system

- Tokens de design (couleurs, espacements, typographie) codés en dur au lieu d'utiliser les variables/tokens définis
- Composants UI dupliqués qui auraient dû réutiliser un composant existant
- Incohérences visuelles entre écrans/composants similaires (paddings, rayons, ombres différents pour un même type d'élément)
- Respect du système de composants existant (shadcn/ui, design tokens custom, etc. selon ce qui est en place)

## 3. Qualité de code

- Lisibilité (nommage clair, fonctions trop longues ou trop denses)
- Duplication de code (DRY)
- Complexité cyclomatique excessive (conditions imbriquées profondes, fonctions qui font trop de choses)
- Gestion des erreurs (try/catch absents ou trop larges, erreurs silencieuses)
- Typage (usage de `any` en TypeScript, absence de typage sur des fonctions critiques)
- Code mort ou commenté laissé en place
- Tests manquants sur une logique critique, si un framework de test est présent dans le projet

## 4. Bonnes pratiques du framework détecté

Adapter selon la stack identifiée à l'étape 1 du SKILL.md. Exemples de points à vérifier si applicable :

- **Next.js / React** : usage correct Server vs Client Components, hooks mal utilisés (dépendances manquantes dans `useEffect`, hooks conditionnels), re-renders inutiles, fetch de données mal placé, gestion des états de chargement/erreur
- **API routes / backend** : validation des entrées, gestion des statuts HTTP, séparation des couches
- **Autres stacks** : appliquer les conventions idiomatiques connues du langage/framework détecté

## 5. Sécurité

- Secrets, clés API ou identifiants en dur dans le code
- Absence de validation/sanitisation des entrées utilisateur
- Injection possible (SQL, commande, XSS) dans les points d'entrée de données
- Contrôles d'accès manquants ou insuffisants sur des routes/actions sensibles
- Dépendances avec vulnérabilités connues (si visible dans `package.json`/lockfile)
- Exposition de données sensibles côté client (variables d'environnement mal préfixées, logs)
- CORS ou headers de sécurité mal configurés

## 6. Performance

- Requêtes réseau/DB redondantes ou en cascade évitables
- Absence de mise en cache pertinente
- Bundles ou imports lourds non nécessaires (import complet d'une lib au lieu d'un import ciblé)
- Images ou assets non optimisés
- Re-renders ou re-calculs coûteux évitables (mémoïsation manquante là où elle serait justifiée, sans en abuser)

## 7. Accessibilité

- Attributs sémantiques HTML manquants (usage de `div`/`span` cliquables au lieu d'éléments interactifs natifs)
- Attributs ARIA manquants ou incorrects là où le HTML sémantique ne suffit pas
- Contraste de couleurs insuffisant si déductible du design system
- Absence de texte alternatif sur les images
- Navigation clavier non gérée sur des éléments interactifs custom
- Labels manquants sur les champs de formulaire
