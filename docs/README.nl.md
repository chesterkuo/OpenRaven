# OpenRaven

**AI-aangedreven kennisassetplatform dat automatisch professionele kennis uit uw documenten extraheert, organiseert en activeert.**

**Lees dit in andere talen:**
[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Español](README.es.md) | **Nederlands** | [Italiano](README.it.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven transformeert verspreide documenten — PDFs, DOCX, presentaties, vergadertranscripties, Notion-exports — in een gestructureerde, doorzoekbare kennisgraaf. Stel vragen in natuurlijke taal, verken verbanden tussen concepten, genereer wiki-artikelen en bouw cursussen op basis van uw kennisbank.

## Waarom OpenRaven?

Professionals verliezen institutionele kennis bij het wisselen van functie of organisatie. Onderzoek toont aan dat 42% van de institutionele kennis alleen in de hoofden van mensen bestaat (IDC). OpenRaven legt die kennis vast en structureert deze zodat ze altijd toegankelijk, doorzoekbaar en deelbaar is.

## Functies

### Kennismotor
- **Slimme ingestie** — Upload PDFs, DOCX, PPTX, XLSX, Markdown, afbeeldingen (AI-visie) of Notion/Obsidian-exports. Entiteiten en relaties worden automatisch geëxtraheerd.
- **Kennisgraaf** — Interactieve krachtsgestuurde graafvisualisatie met filtering op entiteitstype, verbindingssterkte en zoeken. Exporteer als GraphML of PNG.
- **Natuurlijke taal Q&A** — Stel vragen aan uw kennisbank met 6 querymodi (mix, local, global, hybrid, keyword, direct LLM). Antwoorden bevatten bronvermeldingen.
- **Auto-gegenereerde wiki** — Artikelen worden automatisch gegenereerd op basis van geëxtraheerde entiteiten en relaties.
- **Cursusgeneratie** — Maak gestructureerde cursussen op basis van uw kennisbank met curriculumplanning, hoofdstukgeneratie en interactieve HTML-export.
- **Ontdekkingsinzichten** — Automatische analyse van kennisthema's, clusters, hiaten en trends.

### Connectoren
- **Google Drive** — Documenten importeren (PDF, Docs, Sheets, Slides)
- **Gmail** — E-mails importeren als kennisbankvermeldingen
- **Google Meet** — Vergadertranscripties importeren via de Drive API
- **Otter.ai** — Vergadertranscripties importeren via API-sleutel

### Verticale schema's
- **Base** — Algemene entiteitsextractie (standaard)
- **Engineering** — Technische architectuur, systemen, APIs
- **Finance** — Bedrijven, financiële statistieken, regelgeving
- **Legal (Taiwan)** — Statuten, rechterlijke uitspraken, juridische principes (traditioneel Chinees)
- **Finance (Taiwan)** — TWSE-genoteerde bedrijven, financiële statistieken (traditioneel Chinees)

### Meertalige ondersteuning

OpenRaven ondersteunt 12 talen met automatische browserdetectie en handmatige overschrijving:

| Taal | Code | Taal | Code |
|------|------|------|------|
| Engels | `en` | Italiaans | `it` |
| Traditioneel Chinees | `zh-TW` | Vietnamees | `vi` |
| Vereenvoudigd Chinees | `zh-CN` | Thais | `th` |
| Japans | `ja` | Russisch | `ru` |
| Koreaans | `ko` | Frans | `fr` |
| Spaans | `es` | Nederlands | `nl` |

**Hoe het werkt:**
- De browser/OS-locale wordt automatisch gedetecteerd bij het eerste bezoek (standaard: Engels)
- Gebruikers kunnen wisselen via de taalwisselaar in de navigatiebalk
- Voorkeur wordt opgeslagen in localStorage (direct) en gebruikersprofiel (synchronisatie op meerdere apparaten)
- LLM-antwoorden komen overeen met de door de gebruiker geselecteerde taal
- Wiki-artikelen en cursusinhoud volgen de taal van het brondocument
- Labels in de kennisgraaf blijven in het Engels

### Zakelijke functies (beheerde SaaS)
- **Multi-tenant isolatie** — Kennisbanken per huurder met aparte opslag
- **Authenticatie** — E-mail/wachtwoord + Google OAuth 2.0 met sessiebeheer
- **Auditlogboek** — Bijhouden van alle gebruikersacties met CSV-export
- **Teambeheer** — Nodig leden uit voor uw werkruimte
- **Neo4j grafische backend** — Grafische opslag op productieniveau (optioneel, standaard: NetworkX)
- **Docker Compose-implementatie** — Implementatie met één opdracht met nginx, PostgreSQL, Neo4j

## Architectuur

```
openraven/                  # Python-backend (FastAPI + LightRAG + LangExtract)
  src/openraven/
    api/server.py           # FastAPI-applicatiefabriek, alle API-endpoints
    pipeline.py             # Kernpipeline: ingestie, query, graaf, wiki, cursussen
    graph/rag.py            # LightRAG-wrapper met locale-bewuste queries
    auth/                   # Authenticatiesysteem (sessies, OAuth, wachtwoordherstel)
    audit/                  # Module voor auditlogboekregistratie
  alembic/                  # Databasemigraties
  tests/                    # 159+ Python-tests

openraven-ui/               # TypeScript-frontend (React 19 + Vite 6 + Tailwind 4)
  src/
    i18n.ts                 # i18next-initialisatie (12 locales, 11 naamruimten)
    App.tsx                 # Rootcomponent met routes + navigatiebalk
    pages/                  # 14 paginacomponenten
    components/             # LanguageSelector, GraphViewer, ChatMessage, etc.
    hooks/useAuth.tsx       # Authenticatiecontext met locale-synchronisatie
  public/locales/           # 132 vertaling-JSON-bestanden (12 locales x 11 naamruimten)
  server/index.ts           # Hono BFF (API-proxy + statisch bestandsservering)
  tests/                    # 46 Bun-tests

ecosystem.config.cjs        # PM2-implementatieconfiguratie
```

## Snel starten

### Vereisten
- Python 3.12+
- Bun 1.0+
- Node.js 20+ (voor PM2)

### 1. Klonen en installeren

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

### 2. Configureren

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # Vereist: LLM-provider
WORKING_DIR=/path/to/knowledge-data     # Waar kennisbankgegevens worden opgeslagen

# Optioneel: Beheerde SaaS-functies inschakelen
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. Uitvoeren met PM2

```bash
# Vanuit de projectroot
pm2 start ecosystem.config.cjs

# Status controleren
pm2 status

# Logboeken bekijken
pm2 logs
```

Services:
- **openraven-core** (poort 8741) — Python API-server
- **openraven-ui** (poort 3002) — BFF + frontend

### 4. Frontend bouwen voor productie

```bash
cd openraven-ui
bun run build          # Bouwt naar dist/
pm2 restart openraven-ui
```

Open http://localhost:3002 in uw browser.

### Alternatief: Docker Compose

```bash
docker compose up -d
```

Dit start nginx (poort 80), PostgreSQL, Neo4j, de API-server en de UI-server.

## Ontwikkeling

### Tests uitvoeren

```bash
# Backend
cd openraven && python3 -m pytest tests/ -v

# Frontend
cd openraven-ui && bun test tests/

# Benchmarks (vereist GEMINI_API_KEY)
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### Vertalingen toevoegen

Vertaalbestanden bevinden zich in `openraven-ui/public/locales/{locale}/{namespace}.json`.

Om een vertaling toe te voegen of bij te werken:
1. Bewerk het JSON-bestand voor de doellocale
2. Houd sleutels identiek aan het Engelse bronbestand
3. Bewaar `{{interpolation}}`-plaatshouders
4. Voer `bun run build` uit en herstart PM2

Om een nieuwe locale toe te voegen:
1. Maak een nieuwe map aan onder `public/locales/` (bijv. `de/`)
2. Kopieer alle JSON-bestanden vanuit `en/` en vertaal de waarden
3. Voeg de localecode toe aan `SUPPORTED_LNGS` in `src/i18n.ts`
4. Voeg de locale toe aan de `LOCALES`-array in `src/components/LanguageSelector.tsx`
5. Voeg de locale toe aan `SUPPORTED_LOCALES` in `openraven/src/openraven/auth/routes.py`
6. Voeg de localenaam toe aan `LOCALE_NAMES` in `openraven/src/openraven/graph/rag.py`

## API-overzicht

| Methode | Endpoint | Beschrijving |
|---------|----------|--------------|
| `POST` | `/api/ask` | Kennisbank raadplegen (ondersteunt locale-parameter) |
| `POST` | `/api/ingest` | Documenten uploaden en verwerken |
| `GET` | `/api/graph` | Kennisgraafgegevens ophalen |
| `GET` | `/api/wiki` | Wiki-artikelen weergeven |
| `GET` | `/api/status` | Kennisbankstatistieken |
| `GET` | `/api/discovery` | Auto-gegenereerde inzichten |
| `POST` | `/api/courses/generate` | Een cursus genereren |
| `GET` | `/api/connectors/status` | Connectorstatus |
| `PATCH` | `/api/auth/locale` | Localevoorkeur van gebruiker bijwerken |
| `GET` | `/api/audit` | Auditlogboek (gepagineerd) |

Bekijk de volledige API-documentatie op http://localhost:8741/docs (automatisch gegenereerd door FastAPI).

## Technologiestack

| Laag | Technologie |
|------|-------------|
| LLM | Gemini (standaard), Ollama (lokaal) |
| Kennisgraaf | LightRAG + NetworkX (lokaal) / Neo4j (productie) |
| Entiteitsextractie | LangExtract |
| Backend | FastAPI + Uvicorn (Python 3.12) |
| Frontend | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono (Bun runtime) |
| Database | SQLite (lokaal) / PostgreSQL (productie) |
| Authenticatie | Sessiegebaseerd + Google OAuth 2.0 |
| Implementatie | PM2 / Docker Compose |
| Ontwerpsysteem | Mistral Premium (warm ivoor, oranje accenten, gouden schaduwen) |

## Validatieresultaten

- **QA-nauwkeurigheid**: 96,7% (29/30 vragen van niveau 1)
- **Nauwkeurigheid van citaten**: 100% (30/30 bronverwijzingen)
- **LLM-rechterscore**: 4,6/5,0 gemiddeld (niveau 2)
- **Testdekking**: 260+ tests in Python en TypeScript

## Licentie

Apache License 2.0 - zie [LICENSE](LICENSE) voor details.

Copyright 2026 Plusblocks Technology Limited.

## Over

Gebouwd door [Plusblocks Technology Limited](https://plusblocks.com). De kernmotor van OpenRaven is open-source. Cloud- en zakelijke functies (multi-tenant, SSO, facturering) zijn beschikbaar als een beheerde service.
