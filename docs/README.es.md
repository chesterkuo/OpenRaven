# OpenRaven

**Plataforma de activos de conocimiento impulsada por IA que extrae, organiza y activa automáticamente el conocimiento profesional de tus documentos.**

**Leer en otros idiomas:**
[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | **Español** | [Nederlands](README.nl.md) | [Italiano](README.it.md) | [Tiếng Việt](README.vi.md) | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven transforma documentos dispersos — PDFs, DOCX, presentaciones, transcripciones de reuniones, exportaciones de Notion — en un grafo de conocimiento estructurado y consultable. Haz preguntas en lenguaje natural, explora conexiones entre conceptos, genera artículos de wiki y construye cursos a partir de tu base de conocimiento.

## ¿Por qué OpenRaven?

Los profesionales pierden el conocimiento institucional al cambiar de roles u organizaciones. Las investigaciones muestran que el 42 % del conocimiento institucional existe solo en la cabeza de las personas (IDC). OpenRaven captura y estructura ese conocimiento para que siempre sea accesible, buscable y compartible.

## Características

### Motor de conocimiento
- **Ingestión inteligente** — Sube PDFs, DOCX, PPTX, XLSX, Markdown, imágenes (visión IA) o exportaciones de Notion/Obsidian. Las entidades y relaciones se extraen automáticamente.
- **Grafo de conocimiento** — Visualización interactiva del grafo dirigido por fuerzas con filtrado por tipo de entidad, intensidad de conexión y búsqueda. Exportar como GraphML o PNG.
- **Preguntas y respuestas en lenguaje natural** — Consulta tu base de conocimiento con 6 modos de consulta (mix, local, global, hybrid, keyword, direct LLM). Las respuestas incluyen citas de fuentes.
- **Wiki auto-generada** — Los artículos se generan automáticamente a partir de entidades y relaciones extraídas.
- **Generación de cursos** — Crea cursos estructurados a partir de tu base de conocimiento con planificación del currículo, generación de capítulos y exportación HTML interactiva.
- **Perspectivas de descubrimiento** — Análisis automático de temas, clústeres, brechas y tendencias del conocimiento.

### Conectores
- **Google Drive** — Importar documentos (PDF, Docs, Sheets, Slides)
- **Gmail** — Importar correos electrónicos como entradas de la base de conocimiento
- **Google Meet** — Importar transcripciones de reuniones a través de la API de Drive
- **Otter.ai** — Importar transcripciones de reuniones a través de clave API

### Esquemas verticales
- **Base** — Extracción de entidades de propósito general (por defecto)
- **Engineering** — Arquitectura técnica, sistemas, APIs
- **Finance** — Empresas, métricas financieras, regulaciones
- **Legal (Taiwan)** — Estatutos, fallos judiciales, principios legales (chino tradicional)
- **Finance (Taiwan)** — Empresas listadas en TWSE, métricas financieras (chino tradicional)

### Soporte multi-locale

OpenRaven soporta 12 idiomas con detección automática del navegador y cambio manual:

| Idioma | Código | Idioma | Código |
|--------|--------|--------|--------|
| Inglés | `en` | Italiano | `it` |
| Chino tradicional | `zh-TW` | Vietnamita | `vi` |
| Chino simplificado | `zh-CN` | Tailandés | `th` |
| Japonés | `ja` | Ruso | `ru` |
| Coreano | `ko` | Francés | `fr` |
| Español | `es` | Neerlandés | `nl` |

**Cómo funciona:**
- La locale del navegador/OS se detecta automáticamente en la primera visita (predeterminado: inglés)
- Los usuarios pueden cambiar a través del selector de idioma en la barra de navegación
- La preferencia se guarda en localStorage (inmediato) y en el perfil del usuario (sincronización entre dispositivos)
- Las respuestas del LLM coinciden con el idioma seleccionado por el usuario
- Los artículos de wiki y el contenido del curso siguen el idioma del documento fuente
- Las etiquetas del grafo de conocimiento permanecen en inglés

### Características empresariales (SaaS gestionado)
- **Aislamiento multi-tenant** — Bases de conocimiento por inquilino con almacenamiento separado
- **Autenticación** — Correo electrónico/contraseña + Google OAuth 2.0 con gestión de sesiones
- **Registro de auditoría** — Seguimiento de todas las acciones de los usuarios con exportación CSV
- **Gestión de equipos** — Invita miembros a tu espacio de trabajo
- **Backend de grafo Neo4j** — Almacenamiento de grafo de nivel de producción (opcional, por defecto: NetworkX)
- **Despliegue Docker Compose** — Despliegue en un solo comando con nginx, PostgreSQL, Neo4j

## Arquitectura

```
openraven/                  # Backend Python (FastAPI + LightRAG + LangExtract)
  src/openraven/
    api/server.py           # Fábrica de aplicación FastAPI, todos los endpoints de la API
    pipeline.py             # Pipeline principal: ingestión, consulta, grafo, wiki, cursos
    graph/rag.py            # Wrapper de LightRAG con consultas conscientes de la locale
    auth/                   # Sistema de autenticación (sesiones, OAuth, restablecimiento de contraseña)
    audit/                  # Módulo de registro de auditoría
  alembic/                  # Migraciones de base de datos
  tests/                    # 159+ pruebas Python

openraven-ui/               # Frontend TypeScript (React 19 + Vite 6 + Tailwind 4)
  src/
    i18n.ts                 # Inicialización de i18next (12 locales, 11 espacios de nombres)
    App.tsx                 # Componente raíz con rutas + barra de navegación
    pages/                  # 14 componentes de página
    components/             # LanguageSelector, GraphViewer, ChatMessage, etc.
    hooks/useAuth.tsx       # Contexto de autenticación con sincronización de locale
  public/locales/           # 132 archivos JSON de traducción (12 locales x 11 espacios de nombres)
  server/index.ts           # Hono BFF (proxy API + servicio de archivos estáticos)
  tests/                    # 46 pruebas Bun

ecosystem.config.cjs        # Configuración de despliegue PM2
```

## Inicio rápido

### Requisitos previos
- Python 3.12+
- Bun 1.0+
- Node.js 20+ (para PM2)

### 1. Clonar e instalar

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

### 2. Configurar

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # Requerido: proveedor LLM
WORKING_DIR=/path/to/knowledge-data     # Dónde se almacenan los datos de la base de conocimiento

# Opcional: Habilitar características de SaaS gestionado
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. Ejecutar con PM2

```bash
# Desde la raíz del proyecto
pm2 start ecosystem.config.cjs

# Verificar estado
pm2 status

# Ver registros
pm2 logs
```

Servicios:
- **openraven-core** (puerto 8741) — Servidor API Python
- **openraven-ui** (puerto 3002) — BFF + frontend

### 4. Compilar el frontend para producción

```bash
cd openraven-ui
bun run build          # Compila en dist/
pm2 restart openraven-ui
```

Abre http://localhost:3002 en tu navegador.

### Alternativa: Docker Compose

```bash
docker compose up -d
```

Esto inicia nginx (puerto 80), PostgreSQL, Neo4j, el servidor API y el servidor UI.

## Desarrollo

### Ejecutar pruebas

```bash
# Backend
cd openraven && python3 -m pytest tests/ -v

# Frontend
cd openraven-ui && bun test tests/

# Benchmarks (requiere GEMINI_API_KEY)
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### Agregar traducciones

Los archivos de traducción están en `openraven-ui/public/locales/{locale}/{namespace}.json`.

Para agregar o actualizar una traducción:
1. Edita el archivo JSON para la locale de destino
2. Mantén las claves idénticas al archivo fuente en inglés
3. Preserva los marcadores de posición `{{interpolation}}`
4. Ejecuta `bun run build` y reinicia PM2

Para agregar una nueva locale:
1. Crea un nuevo directorio bajo `public/locales/` (ej.: `de/`)
2. Copia todos los archivos JSON desde `en/` y traduce los valores
3. Agrega el código de locale a `SUPPORTED_LNGS` en `src/i18n.ts`
4. Agrega la locale al arreglo `LOCALES` en `src/components/LanguageSelector.tsx`
5. Agrega la locale a `SUPPORTED_LOCALES` en `openraven/src/openraven/auth/routes.py`
6. Agrega el nombre de la locale a `LOCALE_NAMES` en `openraven/src/openraven/graph/rag.py`

## Descripción general de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/ask` | Consultar la base de conocimiento (soporta parámetro locale) |
| `POST` | `/api/ingest` | Subir y procesar documentos |
| `GET` | `/api/graph` | Obtener datos del grafo de conocimiento |
| `GET` | `/api/wiki` | Listar artículos de wiki |
| `GET` | `/api/status` | Estadísticas de la base de conocimiento |
| `GET` | `/api/discovery` | Perspectivas auto-generadas |
| `POST` | `/api/courses/generate` | Generar un curso |
| `GET` | `/api/connectors/status` | Estado de los conectores |
| `PATCH` | `/api/auth/locale` | Actualizar la preferencia de locale del usuario |
| `GET` | `/api/audit` | Registro de auditoría (paginado) |

Ver la documentación completa de la API en http://localhost:8741/docs (auto-generada por FastAPI).

## Stack tecnológico

| Capa | Tecnología |
|------|------------|
| LLM | Gemini (por defecto), Ollama (local) |
| Grafo de conocimiento | LightRAG + NetworkX (local) / Neo4j (producción) |
| Extracción de entidades | LangExtract |
| Backend | FastAPI + Uvicorn (Python 3.12) |
| Frontend | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono (runtime Bun) |
| Base de datos | SQLite (local) / PostgreSQL (producción) |
| Autenticación | Basada en sesión + Google OAuth 2.0 |
| Despliegue | PM2 / Docker Compose |
| Sistema de diseño | Mistral Premium (marfil cálido, acentos naranja, sombras doradas) |

## Resultados de validación

- **Precisión QA**: 96,7 % (29/30 preguntas de nivel 1)
- **Precisión de citas**: 100 % (30/30 referencias de fuentes)
- **Puntuación del juez LLM**: 4,6/5,0 promedio (nivel 2)
- **Cobertura de pruebas**: 260+ pruebas en Python y TypeScript

## Licencia

Apache License 2.0 - ver [LICENSE](LICENSE) para más detalles.

Copyright 2026 Plusblocks Technology Limited.

## Acerca de

Construido por [Plusblocks Technology Limited](https://plusblocks.com). El motor principal de OpenRaven es de código abierto. Las características de nube y empresa (multi-tenant, SSO, facturación) están disponibles como un servicio gestionado.
