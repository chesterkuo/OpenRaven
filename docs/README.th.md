# OpenRaven

**แพลตฟอร์มสินทรัพย์ความรู้ที่ขับเคลื่อนด้วย AI — ดึงข้อมูล จัดระเบียบ และเปิดใช้งานความรู้เชิงวิชาชีพจากเอกสารของคุณโดยอัตโนมัติ**

**อ่านเอกสารนี้ในภาษาอื่น:**
[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Español](README.es.md) | [Nederlands](README.nl.md) | [Italiano](README.it.md) | [Tiếng Việt](README.vi.md) | **ไทย** | [Русский](README.ru.md)

OpenRaven แปลงเอกสารที่กระจัดกระจาย — PDF, DOCX, งานนำเสนอ, บันทึกการประชุม, การส่งออกจาก Notion — ให้เป็นกราฟความรู้ที่มีโครงสร้างและสามารถค้นหาได้ ถามคำถามด้วยภาษาธรรมชาติ สำรวจความเชื่อมโยงระหว่างแนวคิด สร้างบทความวิกิ และสร้างหลักสูตรจากฐานความรู้ของคุณ

## ทำไมต้องเลือก OpenRaven?

ผู้เชี่ยวชาญสูญเสียความรู้ขององค์กรเมื่อเปลี่ยนบทบาทหรือองค์กร งานวิจัยพบว่า 42% ของความรู้ขององค์กรมีอยู่เฉพาะในหัวของผู้คน (IDC) OpenRaven รวบรวมและจัดโครงสร้างความรู้นั้นเพื่อให้เข้าถึง ค้นหา และแบ่งปันได้ตลอดเวลา

## คุณสมบัติ

### เครื่องยนต์ความรู้
- **การนำเข้าอัจฉริยะ** — อัปโหลด PDF, DOCX, PPTX, XLSX, Markdown, รูปภาพ (AI vision) หรือการส่งออกจาก Notion/Obsidian เอนทิตีและความสัมพันธ์ถูกดึงข้อมูลโดยอัตโนมัติ
- **กราฟความรู้** — การแสดงภาพกราฟที่ขับเคลื่อนด้วยแรงแบบโต้ตอบ พร้อมการกรองตามประเภทเอนทิตี ความแข็งแกร่งของการเชื่อมต่อ และการค้นหา ส่งออกเป็น GraphML หรือ PNG
- **ถาม-ตอบด้วยภาษาธรรมชาติ** — ถามคำถามกับฐานความรู้ของคุณโดยใช้โหมดการค้นหา 6 โหมด (mix, local, global, hybrid, keyword, direct LLM) คำตอบมีการอ้างอิงแหล่งที่มา
- **วิกิที่สร้างอัตโนมัติ** — บทความถูกสร้างขึ้นโดยอัตโนมัติจากเอนทิตีและความสัมพันธ์ที่ดึงข้อมูล
- **การสร้างหลักสูตร** — สร้างหลักสูตรที่มีโครงสร้างจากฐานความรู้ของคุณ พร้อมการวางแผนหลักสูตร การสร้างบท และการส่งออก HTML แบบโต้ตอบ
- **ข้อมูลเชิงลึกด้านการค้นพบ** — การวิเคราะห์อัตโนมัติของธีมความรู้ กลุ่ม ช่องว่าง และแนวโน้ม

### ตัวเชื่อมต่อ
- **Google Drive** — นำเข้าเอกสาร (PDF, Docs, Sheets, Slides)
- **Gmail** — นำเข้าอีเมลเป็นรายการในฐานความรู้
- **Google Meet** — นำเข้าบันทึกการประชุมผ่าน Drive API
- **Otter.ai** — นำเข้าบันทึกการประชุมผ่าน API key

### โครงร่างเฉพาะธุรกิจ
- **Base** — การดึงเอนทิตีอเนกประสงค์ (ค่าเริ่มต้น)
- **Engineering** — สถาปัตยกรรมทางเทคนิค ระบบ API
- **Finance** — บริษัท ตัวชี้วัดทางการเงิน กฎระเบียบ
- **Legal (Taiwan)** — กฎหมาย คำพิพากษาของศาล หลักการทางกฎหมาย (ภาษาจีนตัวเต็ม)
- **Finance (Taiwan)** — บริษัทจดทะเบียน TWSE ตัวชี้วัดทางการเงิน (ภาษาจีนตัวเต็ม)

### การรองรับหลายภาษา

OpenRaven รองรับ 12 ภาษาพร้อมการตรวจจับเบราว์เซอร์อัตโนมัติและการเปลี่ยนแปลงด้วยตนเอง:

| ภาษา | รหัส | ภาษา | รหัส |
|------|------|------|------|
| อังกฤษ | `en` | อิตาลี | `it` |
| จีนตัวเต็ม | `zh-TW` | เวียดนาม | `vi` |
| จีนตัวย่อ | `zh-CN` | ไทย | `th` |
| ญี่ปุ่น | `ja` | รัสเซีย | `ru` |
| เกาหลี | `ko` | ฝรั่งเศส | `fr` |
| สเปน | `es` | ดัตช์ | `nl` |

**วิธีการทำงาน:**
- ภาษาของเบราว์เซอร์/ระบบปฏิบัติการถูกตรวจจับอัตโนมัติเมื่อเข้าใช้งานครั้งแรก (ค่าเริ่มต้น: อังกฤษ)
- ผู้ใช้สามารถเปลี่ยนได้ผ่านตัวเลือกภาษาในแถบนำทาง
- การตั้งค่าถูกบันทึกไปยัง localStorage (ทันที) และโปรไฟล์ผู้ใช้ (ซิงค์ข้ามอุปกรณ์)
- การตอบสนองของ LLM ตรงกับภาษาที่ผู้ใช้เลือก
- บทความวิกิและเนื้อหาหลักสูตรตามภาษาเอกสารต้นฉบับ
- ป้ายกำกับกราฟความรู้ยังคงเป็นภาษาอังกฤษ

### คุณสมบัติองค์กร (Managed SaaS)
- **การแยกผู้เช่าหลายราย** — ฐานความรู้แยกต่างหากสำหรับแต่ละผู้เช่าพร้อมพื้นที่เก็บข้อมูลแยกต่างหาก
- **การตรวจสอบตัวตน** — อีเมล/รหัสผ่าน + Google OAuth 2.0 พร้อมการจัดการเซสชัน
- **การบันทึกการตรวจสอบ** — ติดตามการกระทำของผู้ใช้ทั้งหมดพร้อมการส่งออก CSV
- **การจัดการทีม** — เชิญสมาชิกเข้าสู่พื้นที่ทำงานของคุณ
- **Neo4j Graph Backend** — พื้นที่จัดเก็บกราฟระดับการผลิต (ตัวเลือก ค่าเริ่มต้น: NetworkX)
- **การปรับใช้ Docker Compose** — การปรับใช้ด้วยคำสั่งเดียวพร้อม nginx, PostgreSQL, Neo4j

## สถาปัตยกรรม

```
openraven/                  # Python backend (FastAPI + LightRAG + LangExtract)
  src/openraven/
    api/server.py           # FastAPI app factory, API endpoint ทั้งหมด
    pipeline.py             # Pipeline หลัก: นำเข้า, ค้นหา, กราฟ, วิกิ, หลักสูตร
    graph/rag.py            # LightRAG wrapper พร้อมการค้นหาที่รองรับภาษา
    auth/                   # ระบบตรวจสอบตัวตน (เซสชัน, OAuth, รีเซ็ตรหัสผ่าน)
    audit/                  # โมดูลบันทึกการตรวจสอบ
  alembic/                  # การย้ายฐานข้อมูล
  tests/                    # การทดสอบ Python 159+ รายการ

openraven-ui/               # TypeScript frontend (React 19 + Vite 6 + Tailwind 4)
  src/
    i18n.ts                 # การเริ่มต้น i18next (12 ภาษา, 11 namespace)
    App.tsx                 # คอมโพเนนต์รากพร้อม routes + แถบนำทาง
    pages/                  # คอมโพเนนต์หน้า 14 รายการ
    components/             # LanguageSelector, GraphViewer, ChatMessage ฯลฯ
    hooks/useAuth.tsx       # Auth context พร้อมการซิงค์ภาษา
  public/locales/           # ไฟล์ JSON แปลภาษา 132 ไฟล์ (12 ภาษา x 11 namespace)
  server/index.ts           # Hono BFF (API proxy + การให้บริการไฟล์สแตติก)
  tests/                    # การทดสอบ Bun 46 รายการ

ecosystem.config.cjs        # การกำหนดค่าการปรับใช้ PM2
```

## เริ่มต้นอย่างรวดเร็ว

### ข้อกำหนดเบื้องต้น
- Python 3.12+
- Bun 1.0+
- Node.js 20+ (สำหรับ PM2)

### 1. โคลนและติดตั้ง

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

### 2. กำหนดค่า

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # จำเป็น: ผู้ให้บริการ LLM
WORKING_DIR=/path/to/knowledge-data     # ที่เก็บข้อมูลฐานความรู้

# ตัวเลือก: เปิดใช้งานคุณสมบัติ managed SaaS
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. รันด้วย PM2

```bash
# จากไดเรกทอรีรากของโปรเจกต์
pm2 start ecosystem.config.cjs

# ตรวจสอบสถานะ
pm2 status

# ดูบันทึก
pm2 logs
```

บริการ:
- **openraven-core** (พอร์ต 8741) — เซิร์ฟเวอร์ API Python
- **openraven-ui** (พอร์ต 3002) — BFF + frontend

### 4. Build frontend สำหรับการผลิต

```bash
cd openraven-ui
bun run build          # Build ไปยัง dist/
pm2 restart openraven-ui
```

เปิด http://localhost:3002 ในเบราว์เซอร์ของคุณ

### ทางเลือกอื่น: Docker Compose

```bash
docker compose up -d
```

คำสั่งนี้เริ่ม nginx (พอร์ต 80), PostgreSQL, Neo4j, เซิร์ฟเวอร์ API และเซิร์ฟเวอร์ UI

## การพัฒนา

### รันการทดสอบ

```bash
# Backend
cd openraven && python3 -m pytest tests/ -v

# Frontend
cd openraven-ui && bun test tests/

# Benchmarks (ต้องการ GEMINI_API_KEY)
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### การเพิ่มคำแปล

ไฟล์คำแปลอยู่ใน `openraven-ui/public/locales/{locale}/{namespace}.json`

เพื่อเพิ่มหรืออัปเดตคำแปล:
1. แก้ไขไฟล์ JSON สำหรับภาษาเป้าหมาย
2. รักษาคีย์ให้เหมือนกับไฟล์ต้นฉบับภาษาอังกฤษ
3. รักษา placeholder `{{interpolation}}`
4. รัน `bun run build` และรีสตาร์ท PM2

เพื่อเพิ่มภาษาใหม่:
1. สร้างไดเรกทอรีใหม่ใต้ `public/locales/` (เช่น `de/`)
2. คัดลอกไฟล์ JSON ทั้งหมดจาก `en/` และแปลค่าต่างๆ
3. เพิ่มรหัสภาษาใน `SUPPORTED_LNGS` ใน `src/i18n.ts`
4. เพิ่มภาษาในอาร์เรย์ `LOCALES` ใน `src/components/LanguageSelector.tsx`
5. เพิ่มภาษาใน `SUPPORTED_LOCALES` ใน `openraven/src/openraven/auth/routes.py`
6. เพิ่มชื่อภาษาใน `LOCALE_NAMES` ใน `openraven/src/openraven/graph/rag.py`

## ภาพรวม API

| เมธอด | Endpoint | คำอธิบาย |
|-------|----------|----------|
| `POST` | `/api/ask` | ค้นหาฐานความรู้ (รองรับพารามิเตอร์ locale) |
| `POST` | `/api/ingest` | อัปโหลดและประมวลผลเอกสาร |
| `GET` | `/api/graph` | ดึงข้อมูลกราฟความรู้ |
| `GET` | `/api/wiki` | แสดงรายการบทความวิกิ |
| `GET` | `/api/status` | สถิติฐานความรู้ |
| `GET` | `/api/discovery` | ข้อมูลเชิงลึกที่สร้างอัตโนมัติ |
| `POST` | `/api/courses/generate` | สร้างหลักสูตร |
| `GET` | `/api/connectors/status` | สถานะตัวเชื่อมต่อ |
| `PATCH` | `/api/auth/locale` | อัปเดตการตั้งค่าภาษาของผู้ใช้ |
| `GET` | `/api/audit` | บันทึกการตรวจสอบ (แบบแบ่งหน้า) |

ดูเอกสาร API แบบเต็มที่ http://localhost:8741/docs (สร้างอัตโนมัติโดย FastAPI)

## เทคโนโลยีที่ใช้

| ชั้น | เทคโนโลยี |
|------|----------|
| LLM | Gemini (ค่าเริ่มต้น), Ollama (ภายในเครื่อง) |
| กราฟความรู้ | LightRAG + NetworkX (ภายในเครื่อง) / Neo4j (การผลิต) |
| การดึงเอนทิตี | LangExtract |
| Backend | FastAPI + Uvicorn (Python 3.12) |
| Frontend | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono (Bun runtime) |
| ฐานข้อมูล | SQLite (ภายในเครื่อง) / PostgreSQL (การผลิต) |
| การตรวจสอบตัวตน | ตามเซสชัน + Google OAuth 2.0 |
| การปรับใช้ | PM2 / Docker Compose |
| ระบบการออกแบบ | Mistral Premium (งาช้างอบอุ่น, สีส้มเน้น, เงาทอง) |

## ผลการตรวจสอบ

- **ความแม่นยำในการถาม-ตอบ**: 96.7% (29/30 คำถามระดับ 1)
- **ความแม่นยำในการอ้างอิง**: 100% (30/30 การอ้างอิงแหล่งที่มา)
- **คะแนนจาก LLM Judge**: เฉลี่ย 4.6/5.0 (ระดับ 2)
- **ความครอบคลุมการทดสอบ**: การทดสอบ 260+ รายการใน Python และ TypeScript

## สิทธิ์การใช้งาน

Apache License 2.0 — ดู [LICENSE](LICENSE) สำหรับรายละเอียด

ลิขสิทธิ์ 2026 Plusblocks Technology Limited

## เกี่ยวกับ

สร้างโดย [Plusblocks Technology Limited](https://plusblocks.com) เครื่องยนต์หลักของ OpenRaven เป็นโอเพ่นซอร์ส คุณสมบัติระบบคลาวด์และองค์กร (multi-tenant, SSO, การเรียกเก็บเงิน) มีให้บริการในรูปแบบบริการที่จัดการ
