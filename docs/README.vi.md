# OpenRaven

**Nền tảng tài sản tri thức được hỗ trợ bởi AI — tự động trích xuất, tổ chức và kích hoạt tri thức chuyên nghiệp từ tài liệu của bạn.**

**Đọc tài liệu này bằng ngôn ngữ khác:**
[English](../README.md) | [繁體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Français](README.fr.md) | [Español](README.es.md) | [Nederlands](README.nl.md) | [Italiano](README.it.md) | **Tiếng Việt** | [ไทย](README.th.md) | [Русский](README.ru.md)

OpenRaven biến đổi các tài liệu rời rạc — PDF, DOCX, bài thuyết trình, bản ghi cuộc họp, bản xuất Notion — thành một đồ thị tri thức có cấu trúc và có thể truy vấn được. Đặt câu hỏi bằng ngôn ngữ tự nhiên, khám phá các mối liên hệ giữa các khái niệm, tạo bài viết wiki và xây dựng khoá học từ cơ sở tri thức của bạn.

## Tại Sao Chọn OpenRaven?

Các chuyên gia mất đi tri thức tổ chức khi chuyển đổi vai trò hoặc tổ chức. Nghiên cứu cho thấy 42% tri thức tổ chức chỉ tồn tại trong đầu con người (IDC). OpenRaven thu thập và cấu trúc hoá tri thức đó để luôn có thể truy cập, tìm kiếm và chia sẻ.

## Tính Năng

### Bộ Máy Tri Thức
- **Nhập Liệu Thông Minh** — Tải lên PDF, DOCX, PPTX, XLSX, Markdown, hình ảnh (thị giác AI), hoặc bản xuất Notion/Obsidian. Các thực thể và mối quan hệ được trích xuất tự động.
- **Đồ Thị Tri Thức** — Trực quan hoá đồ thị hướng lực tương tác với khả năng lọc theo loại thực thể, cường độ kết nối và tìm kiếm. Xuất dưới dạng GraphML hoặc PNG.
- **Hỏi Đáp Ngôn Ngữ Tự Nhiên** — Đặt câu hỏi cho cơ sở tri thức của bạn bằng 6 chế độ truy vấn (mix, local, global, hybrid, keyword, direct LLM). Câu trả lời bao gồm các trích dẫn nguồn.
- **Wiki Được Tạo Tự Động** — Các bài viết được tự động tạo ra từ các thực thể và mối quan hệ được trích xuất.
- **Tạo Khoá Học** — Tạo các khoá học có cấu trúc từ cơ sở tri thức của bạn với lập kế hoạch chương trình học, tạo chương và xuất HTML tương tác.
- **Khám Phá Thông Tin Chi Tiết** — Phân tích tự động các chủ đề tri thức, cụm, khoảng trống và xu hướng.

### Bộ Kết Nối
- **Google Drive** — Nhập tài liệu (PDF, Docs, Sheets, Slides)
- **Gmail** — Nhập email dưới dạng mục nhập cơ sở tri thức
- **Google Meet** — Nhập bản ghi cuộc họp qua Drive API
- **Otter.ai** — Nhập bản ghi cuộc họp qua API key

### Lược Đồ Theo Ngành
- **Base** — Trích xuất thực thể đa mục đích (mặc định)
- **Engineering** — Kiến trúc kỹ thuật, hệ thống, API
- **Finance** — Công ty, chỉ số tài chính, quy định
- **Legal (Taiwan)** — Đạo luật, phán quyết toà án, nguyên tắc pháp lý (Tiếng Trung Phồn thể)
- **Finance (Taiwan)** — Công ty niêm yết TWSE, chỉ số tài chính (Tiếng Trung Phồn thể)

### Hỗ Trợ Đa Ngôn Ngữ

OpenRaven hỗ trợ 12 ngôn ngữ với tính năng tự động phát hiện ngôn ngữ trình duyệt và tuỳ chỉnh thủ công:

| Ngôn Ngữ | Mã | Ngôn Ngữ | Mã |
|----------|----|----------|----|
| Tiếng Anh | `en` | Tiếng Ý | `it` |
| Tiếng Trung Phồn thể | `zh-TW` | Tiếng Việt | `vi` |
| Tiếng Trung Giản thể | `zh-CN` | Tiếng Thái | `th` |
| Tiếng Nhật | `ja` | Tiếng Nga | `ru` |
| Tiếng Hàn | `ko` | Tiếng Pháp | `fr` |
| Tiếng Tây Ban Nha | `es` | Tiếng Hà Lan | `nl` |

**Cách hoạt động:**
- Ngôn ngữ trình duyệt/HĐH được tự động phát hiện khi truy cập lần đầu (dự phòng: Tiếng Anh)
- Người dùng có thể chuyển đổi qua bộ chọn ngôn ngữ trên thanh điều hướng
- Tuỳ chọn được lưu vào localStorage (ngay lập tức) và hồ sơ người dùng (đồng bộ hoá đa thiết bị)
- Phản hồi LLM khớp với ngôn ngữ đã chọn của người dùng
- Bài viết wiki và nội dung khoá học tuân theo ngôn ngữ tài liệu nguồn
- Nhãn đồ thị tri thức vẫn bằng Tiếng Anh

### Tính Năng Doanh Nghiệp (Managed SaaS)
- **Cách Ly Đa Người Thuê** — Cơ sở tri thức riêng cho từng người thuê với bộ nhớ tách biệt
- **Xác Thực** — Email/mật khẩu + Google OAuth 2.0 với quản lý phiên
- **Ghi Nhật Ký Kiểm Toán** — Theo dõi tất cả hành động người dùng với xuất CSV
- **Quản Lý Nhóm** — Mời thành viên vào không gian làm việc của bạn
- **Neo4j Graph Backend** — Lưu trữ đồ thị cấp độ sản xuất (tuỳ chọn, mặc định: NetworkX)
- **Triển Khai Docker Compose** — Triển khai một lệnh với nginx, PostgreSQL, Neo4j

## Kiến Trúc

```
openraven/                  # Python backend (FastAPI + LightRAG + LangExtract)
  src/openraven/
    api/server.py           # FastAPI app factory, tất cả các API endpoint
    pipeline.py             # Pipeline cốt lõi: nhập liệu, truy vấn, đồ thị, wiki, khoá học
    graph/rag.py            # LightRAG wrapper với truy vấn nhận biết ngôn ngữ
    auth/                   # Hệ thống xác thực (phiên, OAuth, đặt lại mật khẩu)
    audit/                  # Mô-đun ghi nhật ký kiểm toán
  alembic/                  # Di chuyển cơ sở dữ liệu
  tests/                    # 159+ bài kiểm thử Python

openraven-ui/               # TypeScript frontend (React 19 + Vite 6 + Tailwind 4)
  src/
    i18n.ts                 # Khởi tạo i18next (12 ngôn ngữ, 11 namespace)
    App.tsx                 # Thành phần gốc với routes + thanh điều hướng
    pages/                  # 14 thành phần trang
    components/             # LanguageSelector, GraphViewer, ChatMessage, v.v.
    hooks/useAuth.tsx       # Auth context với đồng bộ hoá ngôn ngữ
  public/locales/           # 132 tệp JSON dịch thuật (12 ngôn ngữ x 11 namespace)
  server/index.ts           # Hono BFF (API proxy + phục vụ tệp tĩnh)
  tests/                    # 46 bài kiểm thử Bun

ecosystem.config.cjs        # Cấu hình triển khai PM2
```

## Bắt Đầu Nhanh

### Yêu Cầu Tiên Quyết
- Python 3.12+
- Bun 1.0+
- Node.js 20+ (cho PM2)

### 1. Sao chép và cài đặt

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

### 2. Cấu hình

```bash
# openraven/.env
GEMINI_API_KEY=your-gemini-api-key     # Bắt buộc: nhà cung cấp LLM
WORKING_DIR=/path/to/knowledge-data     # Nơi lưu trữ dữ liệu cơ sở tri thức

# Tuỳ chọn: Kích hoạt tính năng managed SaaS
# DATABASE_URL=postgresql://user:pass@localhost:5433/openraven
# GOOGLE_CLIENT_ID=...
# GOOGLE_CLIENT_SECRET=...
# GRAPH_BACKEND=neo4j
# NEO4J_URI=bolt://localhost:7687
```

### 3. Chạy với PM2

```bash
# Từ thư mục gốc dự án
pm2 start ecosystem.config.cjs

# Kiểm tra trạng thái
pm2 status

# Xem nhật ký
pm2 logs
```

Dịch vụ:
- **openraven-core** (cổng 8741) — Máy chủ API Python
- **openraven-ui** (cổng 3002) — BFF + frontend

### 4. Build frontend cho môi trường sản xuất

```bash
cd openraven-ui
bun run build          # Build vào dist/
pm2 restart openraven-ui
```

Mở http://localhost:3002 trong trình duyệt của bạn.

### Thay Thế: Docker Compose

```bash
docker compose up -d
```

Lệnh này khởi động nginx (cổng 80), PostgreSQL, Neo4j, máy chủ API và máy chủ giao diện người dùng.

## Phát Triển

### Chạy kiểm thử

```bash
# Backend
cd openraven && python3 -m pytest tests/ -v

# Frontend
cd openraven-ui && bun test tests/

# Đánh giá hiệu suất (yêu cầu GEMINI_API_KEY)
GEMINI_API_KEY=<key> python3 -m pytest tests/benchmark/ -v
```

### Thêm bản dịch

Các tệp dịch thuật nằm trong `openraven-ui/public/locales/{locale}/{namespace}.json`.

Để thêm hoặc cập nhật bản dịch:
1. Chỉnh sửa tệp JSON cho ngôn ngữ đích
2. Giữ nguyên các khoá giống với tệp nguồn tiếng Anh
3. Giữ nguyên các placeholder `{{interpolation}}`
4. Chạy `bun run build` và khởi động lại PM2

Để thêm ngôn ngữ mới:
1. Tạo thư mục mới dưới `public/locales/` (ví dụ: `de/`)
2. Sao chép tất cả tệp JSON từ `en/` và dịch các giá trị
3. Thêm mã ngôn ngữ vào `SUPPORTED_LNGS` trong `src/i18n.ts`
4. Thêm ngôn ngữ vào mảng `LOCALES` trong `src/components/LanguageSelector.tsx`
5. Thêm ngôn ngữ vào `SUPPORTED_LOCALES` trong `openraven/src/openraven/auth/routes.py`
6. Thêm tên ngôn ngữ vào `LOCALE_NAMES` trong `openraven/src/openraven/graph/rag.py`

## Tổng Quan API

| Phương Thức | Endpoint | Mô Tả |
|-------------|----------|--------|
| `POST` | `/api/ask` | Truy vấn cơ sở tri thức (hỗ trợ tham số locale) |
| `POST` | `/api/ingest` | Tải lên và xử lý tài liệu |
| `GET` | `/api/graph` | Lấy dữ liệu đồ thị tri thức |
| `GET` | `/api/wiki` | Liệt kê các bài viết wiki |
| `GET` | `/api/status` | Thống kê cơ sở tri thức |
| `GET` | `/api/discovery` | Thông tin chi tiết được tạo tự động |
| `POST` | `/api/courses/generate` | Tạo khoá học |
| `GET` | `/api/connectors/status` | Trạng thái bộ kết nối |
| `PATCH` | `/api/auth/locale` | Cập nhật tuỳ chọn ngôn ngữ người dùng |
| `GET` | `/api/audit` | Nhật ký kiểm toán (phân trang) |

Xem tài liệu API đầy đủ tại http://localhost:8741/docs (được tạo tự động bởi FastAPI).

## Ngăn Xếp Công Nghệ

| Tầng | Công Nghệ |
|------|-----------|
| LLM | Gemini (mặc định), Ollama (nội bộ) |
| Đồ Thị Tri Thức | LightRAG + NetworkX (nội bộ) / Neo4j (sản xuất) |
| Trích Xuất Thực Thể | LangExtract |
| Backend | FastAPI + Uvicorn (Python 3.12) |
| Frontend | React 19 + Vite 6 + Tailwind CSS 4 |
| i18n | react-i18next + i18next-browser-languagedetector |
| BFF | Hono (Bun runtime) |
| Cơ Sở Dữ Liệu | SQLite (nội bộ) / PostgreSQL (sản xuất) |
| Xác Thực | Dựa trên phiên + Google OAuth 2.0 |
| Triển Khai | PM2 / Docker Compose |
| Hệ Thống Thiết Kế | Mistral Premium (ngà voi ấm, điểm nhấn cam, bóng đổ vàng) |

## Kết Quả Kiểm Định

- **Độ Chính Xác Hỏi Đáp**: 96,7% (29/30 câu hỏi Tầng 1)
- **Độ Chính Xác Trích Dẫn**: 100% (30/30 tham chiếu nguồn)
- **Điểm Đánh Giá LLM**: Trung bình 4,6/5,0 (Tầng 2)
- **Độ Phủ Kiểm Thử**: 260+ bài kiểm thử trên Python và TypeScript

## Giấy Phép

Apache License 2.0 — xem [LICENSE](LICENSE) để biết thêm chi tiết.

Bản quyền 2026 Plusblocks Technology Limited.

## Giới Thiệu

Được xây dựng bởi [Plusblocks Technology Limited](https://plusblocks.com). Bộ máy cốt lõi của OpenRaven là mã nguồn mở. Các tính năng đám mây và doanh nghiệp (đa người thuê, SSO, thanh toán) có sẵn dưới dạng dịch vụ được quản lý.
