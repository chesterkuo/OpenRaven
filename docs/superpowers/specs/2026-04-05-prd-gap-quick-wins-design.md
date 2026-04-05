# PRD Gap Analysis — Quick Wins Design Spec

**Date**: 2026-04-05
**Scope**: 4 features identified in PRD gap analysis — query mode UI, image/vision ingestion, Notion/Obsidian import, onboarding "first surprise"
**PRD Reference**: `OpenRaven_PRD_v1.0.md` sections 4.3, 6.1, 6.2, 4.2

---

## Feature 8: Query Mode Selector in Ask UI

### Problem
All 6 LightRAG query modes (local, global, mix, hybrid, naive, bypass) work in CLI and API, but the Ask page hardcodes `mode: "mix"`. Users can't choose query strategies from the UI.

### Design
Add a mode selector dropdown to `AskPage.tsx`.

**UI Component:**
- `<select>` element styled with Mistral Premium design tokens, placed to the left of the send button
- Options with labels and short descriptions:
  - `mix` — "Mix (recommended)" — Specific + broad reasoning
  - `local` — "Local" — Search specific entities
  - `global` — "Global" — Cross-document reasoning
  - `hybrid` — "Hybrid" — Local + global combined
  - `naive` — "Keyword" — Traditional vector search
  - `bypass` — "Direct LLM" — Skip knowledge base
- Default: `mix`

**State:**
- `const [mode, setMode] = useState("mix")`
- Pass `mode` variable to fetch body instead of hardcoded `"mix"`

**Changes:**
| File | Change |
|------|--------|
| `openraven-ui/src/pages/AskPage.tsx` | Add mode state, dropdown, pass to API |

**No backend changes required.**

---

## Feature 10: Image/Vision Ingestion

### Problem
PRD specifies PNG/JPEG/HEIC ingestion via Vision LLM (section 6.2). Currently only text-based formats are supported.

### Design
Use Gemini's multimodal API to extract semantic descriptions from images, then feed into the normal pipeline.

**New function in `parser.py`:**
```python
async def parse_image(file_path: Path) -> ParsedDocument:
    """Send image to Gemini vision API, return extracted description."""
```
- Reads image as base64
- Sends to Gemini via OpenAI-compat client with prompt:
  "Describe this image comprehensively. Extract all visible text, labels, data points, diagrams, relationships, and key information. Format as structured text."
- Returns `ParsedDocument(content=description, metadata={format: "image", ...})`
- Falls back to empty content with error logged if vision API fails

**Pipeline integration:**
- Add to `SUPPORTED_EXTENSIONS`: `.png`, `.jpg`, `.jpeg`, `.heic`, `.webp`
- Route image extensions to `parse_image()` in the parsing step

**UI updates:**
- `FileUploader.tsx`: Add image formats to accept list and display text

**Changes:**
| File | Change |
|------|--------|
| `openraven/src/openraven/ingestion/parser.py` | Add `parse_image()` function |
| `openraven/src/openraven/pipeline.py` | Add image extensions to `SUPPORTED_EXTENSIONS`, route to `parse_image()` |
| `openraven-ui/src/components/FileUploader.tsx` | Add image formats to accept/display |

**Dependencies:** Existing OpenAI-compat client, Gemini API key (already required). No new packages.

---

## Feature 11: Notion/Obsidian Import

### Problem
PRD lists Notion/Obsidian import as open-source feature (section 4.2). Users can manually drag markdown files, but no zip import or format-specific handling exists.

### Design
Add a zip-based import flow that auto-detects and handles both Notion and Obsidian export formats.

**New module: `openraven/src/openraven/ingestion/importers.py`**

```python
def import_zip(zip_path: Path, output_dir: Path) -> list[Path]:
    """Extract and normalize a Notion or Obsidian zip export."""

def _detect_format(zip_file: ZipFile) -> Literal["notion", "obsidian", "generic"]:
    """Auto-detect zip format."""

def _import_notion(zip_file: ZipFile, output_dir: Path) -> list[Path]:
    """Handle Notion export specifics."""

def _import_obsidian(zip_file: ZipFile, output_dir: Path) -> list[Path]:
    """Handle Obsidian export specifics."""
```

**Format detection:**
- Notion markers: filenames with 32-char hex UUID suffixes, `.csv` database exports
- Obsidian markers: `.obsidian/` directory, `[[wikilink]]` syntax in `.md` files
- Fallback: generic — extract all `.md` files as-is

**Notion handler:**
- Strip UUID suffixes from filenames (e.g. `Meeting Notes abc123def456.md` -> `Meeting Notes.md`)
- Convert CSV database exports to markdown tables
- Resolve relative image paths, copy images to output dir

**Obsidian handler:**
- Convert `[[wikilinks]]` to plain text (just the display text)
- Preserve YAML frontmatter (useful metadata)
- Resolve attachment paths from vault's attachment folder
- Skip `.obsidian/` config directory

**Common:**
- Extract all `.md` and `.txt` files
- Copy embedded images to output dir (picked up by Feature 10's vision pipeline)
- Skip binary/config files

**Pipeline integration:**
- Add `.zip` to `SUPPORTED_EXTENSIONS`
- In `add_files()`, detect `.zip` files and call `import_zip()` first
- Feed extracted files into normal pipeline

**API changes:**
- `/api/ingest` already handles file upload — `.zip` files just need to be recognized

**UI changes:**
- Add `.zip` to FileUploader accept list
- Add help text: "Import from Notion or Obsidian — upload your exported .zip file"

**Changes:**
| File | Change |
|------|--------|
| `openraven/src/openraven/ingestion/importers.py` | **New file** — zip import logic |
| `openraven/src/openraven/pipeline.py` | Add `.zip` to extensions, call `import_zip()` for zip files |
| `openraven-ui/src/components/FileUploader.tsx` | Add `.zip` to accept/display |
| `openraven-ui/src/pages/IngestPage.tsx` | Add import help text |

**Dependencies:** `zipfile` (stdlib). No new packages.

---

## Feature 12: Onboarding "First Surprise"

### Problem
PRD section 4.2 describes the "first surprise" as the key retention trigger — users return after first ingestion to find specific, delightful insights about their knowledge. Current discovery is generic stats only.

### Design
Two parts: richer discovery analysis + a notification banner.

### Part A: Enhanced Discovery Insights

Rework `analyze_themes()` in `analyzer.py` to produce specific, actionable insights.

**New insight types:**
1. **"Similar documents"** (type: `cluster`): Group documents by shared entities. "Found 5 documents that share common themes around [topic]"
2. **"Frameworks detected"** (type: `theme`): Identify recurring patterns. "Discovered 12 analysis frameworks you reference frequently"
3. **"Knowledge coverage"** (type: `theme`): Topic distribution. "Your knowledge spans 8 areas, strongest in [top topic] (34 entities)"
4. **"Connections discovered"** (type: `trend`): Cross-document links. "Documents about [A] and [B] share 3 common concepts"
5. **"Knowledge gaps"** (type: `gap`): Isolated nodes or thin areas. "Topic [X] has only 2 sources — consider adding more material"

**Input data:** Use graph nodes (with types), edges (with descriptions), and connected components from NetworkX/Neo4j. The existing `get_stats()` returns node/edge counts; we need to also pull entity type distribution and top connected components.

**New helper in `rag.py`:**
```python
def get_detailed_stats(self) -> dict:
    """Return node type distribution, top clusters, and cross-links."""
```

### Part B: Onboarding Banner

**New component: `OnboardingBanner.tsx`**
- Shown on AskPage when:
  1. `/api/status` reports `total_files > 0` (knowledge base has content)
  2. `localStorage.getItem("onboarding_dismissed")` is not set
- Content: "Your knowledge base is ready! We found {entity_count} concepts across {topic_count} topics. Ask a question to explore."
- Dismiss button sets localStorage flag
- Styled: cream background (`--color-surface-secondary`), orange left border (`--color-accent`), golden shadow

**Changes:**
| File | Change |
|------|--------|
| `openraven/src/openraven/discovery/analyzer.py` | Rework `analyze_themes()` with richer insights |
| `openraven/src/openraven/graph/rag.py` | Add `get_detailed_stats()` method |
| `openraven-ui/src/components/OnboardingBanner.tsx` | **New file** — banner component |
| `openraven-ui/src/pages/AskPage.tsx` | Integrate OnboardingBanner |

---

## Testing Strategy

| Feature | Tests |
|---------|-------|
| 8: Query Mode | Manual — verify dropdown sends correct mode, check each mode returns results |
| 10: Image Vision | Unit test `parse_image()` with mock Gemini response; integration test image file through pipeline |
| 11: Zip Import | Unit tests for `_detect_format()`, `_import_notion()`, `_import_obsidian()`; test with sample zips |
| 12: Onboarding | Unit test enhanced `analyze_themes()` with sample graph data; manual test banner show/dismiss |

---

## Out of Scope

- Notion API live sync (only exported zip files)
- Obsidian plugin integration
- Image OCR fallback (Tesseract) — Gemini vision is sufficient
- Query mode persistence across sessions
- Advanced onboarding wizard / multi-step tutorial
