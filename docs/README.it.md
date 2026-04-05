# OpenRaven

**Piattaforma di asset di conoscenza alimentata dall'IA che estrae, organizza e attiva automaticamente la conoscenza professionale dai tuoi documenti.**

**Leggi in altre lingue:**
[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Español](README.es.md) | [Nederlands](README.nl.md) | **Italiano** | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven trasforma documenti sparsi — PDF, DOCX, presentazioni, trascrizioni di riunioni, esportazioni di Notion — in un grafo di conoscenza strutturato e interrogabile. Fai domande in linguaggio naturale, esplora le connessioni tra concetti, genera articoli wiki e crea corsi dalla tua base di conoscenza.

## Perché OpenRaven?

I professionisti perdono la conoscenza istituzionale quando cambiano ruolo o organizzazione. Le ricerche mostrano che il 42% della conoscenza istituzionale esiste solo nella testa delle persone (IDC). OpenRaven cattura e struttura quella conoscenza in modo che sia sempre accessibile, ricercabile e condivisibile.

## Funzionalità

### Motore di conoscenza
- **Ingestione intelligente** — Carica PDF, DOCX, PPTX, XLSX, Markdown, immagini (visione IA) o esportazioni Notion/Obsidian. Entità e relazioni vengono estratte automaticamente.
- **Grafo di conoscenza** — Visualizzazione interattiva del grafo a forza diretta con filtro per tipo di entità, intensità di connessione e ricerca. Esporta come GraphML o PNG.
- **Domande e risposte in linguaggio naturale** — Interroga la tua base di conoscenza con 6 modalità di query (mix, local, global, hybrid, keyword, direct LLM). Le risposte includono citazioni delle fonti.
- **Wiki auto-generata** — Gli articoli vengono generati automaticamente da entità e relazioni estratte.
- **Generazione di corsi** — Crea corsi strutturati dalla tua base di conoscenza con pianificazione del curriculum, generazione di capitoli ed esportazione HTML interattiva.
- **Approfondimenti di scoperta** — Analisi automatica di temi, cluster, lacune e tendenze della conoscenza.

### Connettori
- **Google Drive** — Importa documenti (PDF, Docs, Sheets, Slides)
- **Gmail** — Importa e-mail come voci della base di conoscenza
- **Google Meet** — Importa trascrizioni di riunioni tramite l'API Drive
- **Otter.ai** — Importa trascrizioni di riunioni tramite chiave API

### Schemi verticali
- **Base** — Estrazione di entità per uso generale (predefinito)
- **Engineering** — Architettura tecnica, sistemi, APIs
- **Finance** — Aziende, metriche finanziarie, regolamentazioni
- **Legal (Taiwan)** — Statuti, sentenze, principi giuridici (cinese tradizionale)
- **Finance (Taiwan)** — Aziende quotate al TWSE, metriche finanziarie (cinese tradizionale)

### Supporto multi-locale

OpenRaven supporta 12 lingue con rilevamento automatico del browser e sostituzione manuale:

| Lingua | Codice | Lingua | Codice |
|--------|--------|--------|--------|
| Inglese | `en` | Italiano | `it` |
| Cinese tradizionale | `zh-TW` | Vietnamita | `vi` |
| Cinese semplificato | `zh-CN` | Tailandese | `th` |
| Giapponese | `ja` | Russo | `ru` |
| Coreano | `ko` | Francese | `fr` |
| Spagnolo | `es` | Olandese | `nl` |

**Come funziona:**
- La locale del browser/OS viene rilevata automaticamente alla prima visita (predefinito: inglese)
- Gli utenti possono cambiare tramite il selettore di lingua nella barra di navigazione
- La preferenza viene salvata in localStorage (immediato) e nel profilo utente (sincronizzazione multi-dispositivo)
- Le risposte LLM corrispondono alla lingua selezionata dall'utente
- Gli articoli wiki e il contenuto dei corsi seguono la lingua del documento sorgente
- Le etichette del grafo di conoscenza rimangono in inglese

### Funzionalità aziendali (SaaS gestito)
- **Isolamento multi-tenant** — Basi di conoscenza per tenant con archiviazione separata
- **Autenticazione** — E-mail/password + Google OAuth 2.0 con gestione delle sessioni
- **Registro di audit** — Tracciamento di tutte le azioni degli utenti con esportazione CSV
- **Gestione del team** — Invita membri nel tuo spazio di lavoro
- **Backend grafo Neo4j** — Archiviazione grafo di livello produzione (opzionale, predefinito: NetworkX)
- **Distribuzione Docker Compose** — Distribuzione con un solo comando con nginx, PostgreSQL, Neo4j

## Architettura

```
openraven/                  # Backend Python (FastAPI + LightRAG + LangExtract)
  src/openraven/
    api/server.py           # Factory dell'applicazione FastAPI, tutti gli endpoint API
    pipeline.py             # Pipeline principale: ingestione, query, grafo, wiki, corsi
    graph/rag.py            # Wrapper LightRAG con query consapevoli della locale
    auth/                   # Sistema di autenticazione (sessioni, OAuth, reset password)
    audit/                  # Modulo di registrazione audit
  alembic/                  # Migrazioni del database
  tests/                    # 159+ test Python

openraven-ui/               # Frontend TypeScript (React 19 + Vite 6 + Tailwind 4)
  src/
    i18n.ts                 # Inizializzazione i18next (12 locali, 11 spazi dei nomi)
    App.tsx                 # Componente radice con route + barra di navigazione
    pages/                  # 14 componenti di pagina
    components/             # LanguageSelector, GraphViewer, ChatMessage, ecc.
    hooks/useAuth.tsx       # Contesto di autenticazione con sincronizzazione locale
  public/locales/           # 132 file JSON di traduzione (12 locali x 11 spazi dei nomi)
  server/index.ts           # Hono BFF (proxy API + servizio file statici)
  tests/                    # 46 test Bun

ecosystem.config.cjs        # Configurazione di distribuzione PM2
```

## Avvio rapido

### Prerequisiti
- Python 3.12+
- Bun 1.0+
- Node.js 20+ (per PM2)

### 1. Clonare e installare

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

### 2. Configurare

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # Richiesto: provider LLM
WORKING_DIR=/path/to/knowledge-data     # Dove vengono archiviati i dati della base di conoscenza

# Opzionale: Abilitare le funzionalità SaaS gestito
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. Eseguire con PM2

```bash
# Dalla radice del progetto
pm2 start ecosystem.config.cjs

# Controllare lo stato
pm2 status

# Visualizzare i log
pm2 logs
```

Servizi:
- **openraven-core** (porta 8741) — Server API Python
- **openraven-ui** (porta 3002) — BFF + frontend

### 4. Compilare il frontend per la produzione

```bash
cd openraven-ui
bun run build          # Compila in dist/
pm2 restart openraven-ui
```

Apri http://localhost:3002 nel tuo browser.

### Alternativa: Docker Compose

```bash
docker compose up -d
```

Questo avvia nginx (porta 80), PostgreSQL, Neo4j, il server API e il server UI.

## Sviluppo

### Eseguire i test

```bash
# Backend
cd openraven && python3 -m pytest tests/ -v

# Frontend
cd openraven-ui && bun test tests/

# Benchmark (richiede GEMINI_API_KEY)
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### Aggiungere traduzioni

I file di traduzione si trovano in `openraven-ui/public/locales/{locale}/{namespace}.json`.

Per aggiungere o aggiornare una traduzione:
1. Modifica il file JSON per la locale di destinazione
2. Mantieni le chiavi identiche al file sorgente inglese
3. Preserva i segnaposto `{{interpolation}}`
4. Esegui `bun run build` e riavvia PM2

Per aggiungere una nuova locale:
1. Crea una nuova directory sotto `public/locales/` (es. `de/`)
2. Copia tutti i file JSON da `en/` e traduci i valori
3. Aggiungi il codice locale a `SUPPORTED_LNGS` in `src/i18n.ts`
4. Aggiungi la locale all'array `LOCALES` in `src/components/LanguageSelector.tsx`
5. Aggiungi la locale a `SUPPORTED_LOCALES` in `openraven/src/openraven/auth/routes.py`
6. Aggiungi il nome della locale a `LOCALE_NAMES` in `openraven/src/openraven/graph/rag.py`

## Panoramica dell'API

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| `POST` | `/api/ask` | Interrogare la base di conoscenza (supporta il parametro locale) |
| `POST` | `/api/ingest` | Caricare ed elaborare documenti |
| `GET` | `/api/graph` | Ottenere i dati del grafo di conoscenza |
| `GET` | `/api/wiki` | Elencare gli articoli wiki |
| `GET` | `/api/status` | Statistiche della base di conoscenza |
| `GET` | `/api/discovery` | Approfondimenti auto-generati |
| `POST` | `/api/courses/generate` | Generare un corso |
| `GET` | `/api/connectors/status` | Stato dei connettori |
| `PATCH` | `/api/auth/locale` | Aggiornare la preferenza di locale dell'utente |
| `GET` | `/api/audit` | Registro di audit (paginato) |

Consulta la documentazione completa dell'API su http://localhost:8741/docs (auto-generata da FastAPI).

## Stack tecnologico

| Livello | Tecnologia |
|---------|------------|
| LLM | Gemini (predefinito), Ollama (locale) |
| Grafo di conoscenza | LightRAG + NetworkX (locale) / Neo4j (produzione) |
| Estrazione di entità | LangExtract |
| Backend | FastAPI + Uvicorn (Python 3.12) |
| Frontend | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono (runtime Bun) |
| Database | SQLite (locale) / PostgreSQL (produzione) |
| Autenticazione | Basata su sessione + Google OAuth 2.0 |
| Distribuzione | PM2 / Docker Compose |
| Sistema di design | Mistral Premium (avorio caldo, accenti arancioni, ombre dorate) |

## Risultati di validazione

- **Accuratezza QA**: 96,7% (29/30 domande di livello 1)
- **Accuratezza delle citazioni**: 100% (30/30 riferimenti alle fonti)
- **Punteggio del giudice LLM**: 4,6/5,0 medio (livello 2)
- **Copertura dei test**: 260+ test in Python e TypeScript

## Licenza

Apache License 2.0 - vedere [LICENSE](LICENSE) per i dettagli.

Copyright 2026 Plusblocks Technology Limited.

## Informazioni

Realizzato da [Plusblocks Technology Limited](https://plusblocks.com). Il motore principale di OpenRaven è open-source. Le funzionalità cloud e aziendali (multi-tenant, SSO, fatturazione) sono disponibili come servizio gestito.
