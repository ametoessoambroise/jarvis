# Format du rapport

## Fichier par fichier audité : `audit/<nom_fichier>.md`

```markdown
# Audit — <chemin/du/fichier>

**Stack détectée** : <ex. Next.js 15 / TypeScript / Tailwind>
**Findings** : X critique(s), Y majeur(s), Z mineur(s)

---

## [CRITIQUE] <Titre court du problème>

- **Catégorie** : Sécurité
- **Ligne(s)** : 42-47
- **Problème** : <description précise et factuelle>
- **Impact** : <conséquence concrète>
- **Correction proposée** :

\`\`\`ts
// avant
...

// après
...
\`\`\`

---

## [MAJEUR] <Titre court du problème>

- **Catégorie** : Qualité de code
- **Ligne(s)** : 12
- **Problème** : ...
- **Impact** : ...
- **Correction proposée** : ...

---

(un bloc par finding, triés par sévérité décroissante : Critique → Majeur → Mineur)
```

Si aucun finding sur un fichier, générer quand même `audit/<nom_fichier>.md` avec une ligne : "Aucun problème significatif détecté." — ne pas inventer de findings pour paraître exhaustif.

## Synthèse globale : `audit/SYNTHESE.md`

```markdown
# Synthèse d'audit — <nom du projet ou dossier audité>

**Stack détectée** : <...>
**Fichiers audités** : N
**Findings totaux** : X critique(s), Y majeur(s), Z mineur(s)

## Vue d'ensemble

<3-5 lignes résumant l'état général du projet>

## Répartition par catégorie

| Catégorie | Critique | Majeur | Mineur |
|---|---|---|---|
| Architecture | | | |
| Design system | | | |
| Qualité de code | | | |
| Bonnes pratiques framework | | | |
| Sécurité | | | |
| Performance | | | |
| Accessibilité | | | |

## Risques transverses

<Patterns qui reviennent dans plusieurs fichiers — ex. une même faille de validation répétée sur plusieurs routes, une incohérence de tokens de couleur répandue>

## Priorités de correction recommandées

1. <finding ou groupe de findings à traiter en premier, avec justification>
2. ...
3. ...
```
