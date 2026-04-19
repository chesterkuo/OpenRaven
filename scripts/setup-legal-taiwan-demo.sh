#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SOURCE_DIR="$PROJECT_ROOT/openraven/data/demo/legal-taiwan"
TARGET_DIR="/data/tenants/demo/legal-taiwan"

echo "=== OpenRaven 台灣法律 Demo 設置 ==="
echo ""

# 1. Copy files to demo tenant directory
echo "[1/3] 複製文件到 $TARGET_DIR ..."
sudo mkdir -p "$TARGET_DIR"
sudo cp -r "$SOURCE_DIR"/* "$SOURCE_DIR"/.theme.json "$TARGET_DIR/"
sudo chown -R ubuntu:ubuntu "$TARGET_DIR"
echo "      已複製 $(ls "$TARGET_DIR"/*.md 2>/dev/null | wc -l) 份文件 + .theme.json"

# 2. Verify theme is visible
echo ""
echo "[2/3] 驗證主題是否可被偵測..."
if [ -f "$TARGET_DIR/.theme.json" ]; then
    echo "      .theme.json 存在 ✓"
    cat "$TARGET_DIR/.theme.json" | python3 -m json.tool > /dev/null 2>&1 && echo "      JSON 格式正確 ✓" || echo "      JSON 格式錯誤 ✗"
else
    echo "      .theme.json 不存在 ✗"
    exit 1
fi

# 3. Trigger ingestion via API
echo ""
echo "[3/3] 觸發文件 ingestion..."
echo ""
echo "  方式 A — 透過 API（需要先啟動 OpenRaven 服務）:"
echo ""
echo "    # 先登入取得 session（或使用 demo session）"
echo "    curl -s http://localhost:8741/api/demo/themes | python3 -m json.tool"
echo ""
echo "    # 確認 legal-taiwan 主題出現後，建立 demo session"
echo "    curl -X POST http://localhost:8741/api/auth/demo \\"
echo "         -H 'Content-Type: application/json' \\"
echo "         -d '{\"theme\": \"legal-taiwan\"}' -c /tmp/demo-cookie.txt"
echo ""
echo "    # 用取得的 session cookie 進行 ingestion"
echo "    for f in $TARGET_DIR/*.md; do"
echo "      curl -X POST http://localhost:8741/api/ingest \\"
echo "           -F \"files=@\$f\" \\"
echo "           -F \"schema=legal-taiwan\" \\"
echo "           -b /tmp/demo-cookie.txt"
echo "    done"
echo ""
echo "  方式 B — 透過 Python CLI（直接執行 pipeline）:"
echo ""
echo "    cd $PROJECT_ROOT/openraven"
echo "    source .venv/bin/activate"
echo "    python3 -c \""
echo "    import asyncio"
echo "    from pathlib import Path"
echo "    from openraven.config import RavenConfig"
echo "    from openraven.pipeline import RavenPipeline"
echo ""
echo "    async def ingest():"
echo "        config = RavenConfig(working_dir='$TARGET_DIR')"
echo "        pipeline = RavenPipeline(config)"
echo "        files = list(Path('$TARGET_DIR').glob('*.md'))"
echo "        print(f'Ingesting {len(files)} files...')"
echo "        result = await pipeline.add_files(files, schema_name='legal-taiwan')"
echo "        print(f'Done: {result.documents_processed} docs, {result.entities_extracted} entities')"
echo ""
echo "    asyncio.run(ingest())"
echo "    \""
echo ""
echo "=== 設置完成 ==="
echo ""
echo "文件列表："
ls -la "$TARGET_DIR"/*.md
echo ""
echo "下一步：選擇上面的方式 A 或 B 來執行 ingestion"
echo "完成後，到 openraven.cc 選擇「台灣法律文件」主題即可體驗"
