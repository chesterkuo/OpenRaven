# OpenRaven

**Plateforme d'actifs de connaissance propulsée par l'IA qui extrait, organise et active automatiquement les connaissances professionnelles à partir de vos documents.**

**Lire dans d'autres langues :**
[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | **Français** | [Español](README.es.md) | [Nederlands](README.nl.md) | [Italiano](README.it.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven transforme les documents éparpillés — PDFs, DOCX, présentations, transcriptions de réunions, exports Notion — en un graphe de connaissances structuré et interrogeable. Posez des questions en langage naturel, explorez les connexions entre les concepts, générez des articles de wiki et créez des cours à partir de votre base de connaissances.

## Pourquoi OpenRaven ?

Les professionnels perdent les connaissances institutionnelles lors des changements de poste ou d'organisation. Les recherches montrent que 42 % des connaissances institutionnelles n'existent que dans la tête des gens (IDC). OpenRaven capture et structure ces connaissances afin qu'elles soient toujours accessibles, recherchables et partageables.

## Fonctionnalités

### Moteur de connaissances
- **Ingestion intelligente** — Téléchargez des PDFs, DOCX, PPTX, XLSX, Markdown, images (vision IA) ou des exports Notion/Obsidian. Les entités et les relations sont extraites automatiquement.
- **Graphe de connaissances** — Visualisation interactive du graphe dirigé par la force avec filtrage par type d'entité, intensité de connexion et recherche. Export au format GraphML ou PNG.
- **Questions-Réponses en langage naturel** — Interrogez votre base de connaissances avec 6 modes de requête (mix, local, global, hybrid, keyword, direct LLM). Les réponses incluent des citations de sources.
- **Wiki auto-généré** — Les articles sont automatiquement générés à partir des entités et des relations extraites.
- **Génération de cours** — Créez des cours structurés à partir de votre base de connaissances avec planification du programme, génération de chapitres et export HTML interactif.
- **Insights de découverte** — Analyse automatique des thèmes, clusters, lacunes et tendances des connaissances.

### Connecteurs
- **Google Drive** — Importer des documents (PDF, Docs, Sheets, Slides)
- **Gmail** — Importer des e-mails comme entrées de base de connaissances
- **Google Meet** — Importer des transcriptions de réunions via l'API Drive
- **Otter.ai** — Importer des transcriptions de réunions via une clé API

### Schémas verticaux
- **Base** — Extraction d'entités à usage général (par défaut)
- **Engineering** — Architecture technique, systèmes, APIs
- **Finance** — Entreprises, métriques financières, réglementations
- **Legal (Taiwan)** — Statuts, décisions de justice, principes juridiques (chinois traditionnel)
- **Finance (Taiwan)** — Sociétés cotées au TWSE, métriques financières (chinois traditionnel)

### Support multi-locale

OpenRaven prend en charge 12 langues avec détection automatique du navigateur et substitution manuelle :

| Langue | Code | Langue | Code |
|--------|------|--------|------|
| Anglais | `en` | Italien | `it` |
| Chinois traditionnel | `zh-TW` | Vietnamien | `vi` |
| Chinois simplifié | `zh-CN` | Thaï | `th` |
| Japonais | `ja` | Russe | `ru` |
| Coréen | `ko` | Français | `fr` |
| Espagnol | `es` | Néerlandais | `nl` |

**Comment ça fonctionne :**
- La locale du navigateur/OS est auto-détectée à la première visite (par défaut : anglais)
- Les utilisateurs peuvent changer via le sélecteur de langue dans la barre de navigation
- La préférence est sauvegardée dans localStorage (immédiat) et le profil utilisateur (synchronisation multi-appareils)
- Les réponses LLM correspondent à la langue sélectionnée par l'utilisateur
- Les articles wiki et le contenu des cours suivent la langue du document source
- Les étiquettes du graphe de connaissances restent en anglais

### Fonctionnalités entreprise (SaaS géré)
- **Isolation multi-tenant** — Bases de connaissances par locataire avec stockage séparé
- **Authentification** — E-mail/mot de passe + Google OAuth 2.0 avec gestion de session
- **Journal d'audit** — Suivi de toutes les actions utilisateurs avec export CSV
- **Gestion d'équipe** — Invitez des membres dans votre espace de travail
- **Backend graphe Neo4j** — Stockage de graphe de niveau production (optionnel, par défaut : NetworkX)
- **Déploiement Docker Compose** — Déploiement en une commande avec nginx, PostgreSQL, Neo4j

## Architecture

```
openraven/                  # Backend Python (FastAPI + LightRAG + LangExtract)
  src/openraven/
    api/server.py           # Fabrique d'application FastAPI, tous les endpoints API
    pipeline.py             # Pipeline principal : ingestion, requête, graphe, wiki, cours
    graph/rag.py            # Wrapper LightRAG avec requêtes sensibles à la locale
    auth/                   # Système d'authentification (sessions, OAuth, réinitialisation de mot de passe)
    audit/                  # Module de journalisation d'audit
  alembic/                  # Migrations de base de données
  tests/                    # 159+ tests Python

openraven-ui/               # Frontend TypeScript (React 19 + Vite 6 + Tailwind 4)
  src/
    i18n.ts                 # Initialisation i18next (12 locales, 11 espaces de noms)
    App.tsx                 # Composant racine avec routes + barre de navigation
    pages/                  # 14 composants de page
    components/             # LanguageSelector, GraphViewer, ChatMessage, etc.
    hooks/useAuth.tsx       # Contexte d'authentification avec synchronisation de locale
  public/locales/           # 132 fichiers JSON de traduction (12 locales x 11 espaces de noms)
  server/index.ts           # Hono BFF (proxy API + service de fichiers statiques)
  tests/                    # 46 tests Bun

ecosystem.config.cjs        # Configuration de déploiement PM2
```

## Démarrage rapide

### Prérequis
- Python 3.12+
- Bun 1.0+
- Node.js 20+ (pour PM2)

### 1. Cloner et installer

```bash
git clone https://github.com/nickhealthy/OpenRaven.git
cd OpenRaven

# Backend
cd openraven
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd ../openraven-ui
bun install
```

### 2. Configurer

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # Requis : fournisseur LLM
WORKING_DIR=/path/to/knowledge-data     # Où les données de la base de connaissances sont stockées

# Optionnel : Activer les fonctionnalités SaaS géré
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. Lancer avec PM2

```bash
# Depuis la racine du projet
pm2 start ecosystem.config.cjs

# Vérifier le statut
pm2 status

# Voir les journaux
pm2 logs
```

Services :
- **openraven-core** (port 8741) — Serveur API Python
- **openraven-ui** (port 3002) — BFF + frontend

### 4. Compiler le frontend pour la production

```bash
cd openraven-ui
bun run build          # Compile vers dist/
pm2 restart openraven-ui
```

Ouvrez http://localhost:3002 dans votre navigateur.

### Alternative : Docker Compose

```bash
docker compose up -d
```

Cela démarre nginx (port 80), PostgreSQL, Neo4j, le serveur API et le serveur UI.

## Développement

### Exécuter les tests

```bash
# Backend
cd openraven && python3 -m pytest tests/ -v

# Frontend
cd openraven-ui && bun test tests/

# Benchmarks (nécessite GEMINI_API_KEY)
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### Ajouter des traductions

Les fichiers de traduction se trouvent dans `openraven-ui/public/locales/{locale}/{namespace}.json`.

Pour ajouter ou mettre à jour une traduction :
1. Modifiez le fichier JSON pour la locale cible
2. Conservez les clés identiques au fichier source anglais
3. Préservez les espaces réservés `{{interpolation}}`
4. Exécutez `bun run build` et redémarrez PM2

Pour ajouter une nouvelle locale :
1. Créez un nouveau répertoire sous `public/locales/` (ex. : `de/`)
2. Copiez tous les fichiers JSON depuis `en/` et traduisez les valeurs
3. Ajoutez le code de locale à `SUPPORTED_LNGS` dans `src/i18n.ts`
4. Ajoutez la locale au tableau `LOCALES` dans `src/components/LanguageSelector.tsx`
5. Ajoutez la locale à `SUPPORTED_LOCALES` dans `openraven/src/openraven/auth/routes.py`
6. Ajoutez le nom de la locale à `LOCALE_NAMES` dans `openraven/src/openraven/graph/rag.py`

## Aperçu de l'API

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/ask` | Interroger la base de connaissances (supporte le paramètre locale) |
| `POST` | `/api/ingest` | Télécharger et traiter des documents |
| `GET` | `/api/graph` | Obtenir les données du graphe de connaissances |
| `GET` | `/api/wiki` | Lister les articles wiki |
| `GET` | `/api/status` | Statistiques de la base de connaissances |
| `GET` | `/api/discovery` | Insights auto-générés |
| `POST` | `/api/courses/generate` | Générer un cours |
| `GET` | `/api/connectors/status` | Statut des connecteurs |
| `PATCH` | `/api/auth/locale` | Mettre à jour la préférence de locale de l'utilisateur |
| `GET` | `/api/audit` | Journal d'audit (paginé) |

Voir la documentation complète de l'API sur http://localhost:8741/docs (auto-générée par FastAPI).

## Stack technologique

| Couche | Technologie |
|--------|-------------|
| LLM | Gemini (par défaut), Ollama (local) |
| Graphe de connaissances | LightRAG + NetworkX (local) / Neo4j (production) |
| Extraction d'entités | LangExtract |
| Backend | FastAPI + Uvicorn (Python 3.12) |
| Frontend | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono (runtime Bun) |
| Base de données | SQLite (local) / PostgreSQL (production) |
| Authentification | Basée sur session + Google OAuth 2.0 |
| Déploiement | PM2 / Docker Compose |
| Système de design | Mistral Premium (ivoire chaud, accents orange, ombres dorées) |

## Résultats de validation

- **Précision QA** : 96,7 % (29/30 questions de niveau 1)
- **Précision des citations** : 100 % (30/30 références de sources)
- **Score du juge LLM** : 4,6/5,0 en moyenne (niveau 2)
- **Couverture des tests** : 260+ tests en Python et TypeScript

## Licence

Apache License 2.0 - voir [LICENSE](LICENSE) pour les détails.

Copyright 2026 Plusblocks Technology Limited.

## À propos

Construit par [Plusblocks Technology Limited](https://plusblocks.com). Le moteur principal d'OpenRaven est open-source. Les fonctionnalités cloud et entreprise (multi-tenant, SSO, facturation) sont disponibles en tant que service géré.
