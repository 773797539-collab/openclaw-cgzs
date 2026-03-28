#!/bin/bash
# export-docs.sh - 主文档导出脚本
# 用途：将 Markdown 主文档导出为 DOCX 阅读版
# 依赖：pandoc
# 使用：bash scripts/export-docs.sh

set -e

PROJECT_ROOT="/home/admin/openclaw/workspace"
EXPORT_DIR="$PROJECT_ROOT/exports"
MAIN_DOC="$PROJECT_ROOT/docs/实施总文档_v2.2.md"
EXPORT_FILE="$EXPORT_DIR/实施总文档_$(date +%Y%m%d).docx"

echo "📄 开始导出主文档..."

# 确保导出目录存在
mkdir -p "$EXPORT_DIR"

# 导出 DOCX
pandoc "$MAIN_DOC" \
  -o "$EXPORT_FILE" \
  --reference-doc=/usr/share/pandoc/data/reference.docx 2>/dev/null \
  || pandoc "$MAIN_DOC" -o "$EXPORT_FILE"

# 同时生成当日快照
SNAPSHOT="$EXPORT_DIR/实施总文档_$(date +%Y%m%d_%H%M).docx"
cp "$EXPORT_FILE" "$SNAPSHOT"

# 更新符号链接到最新
ln -sf "$EXPORT_FILE" "$EXPORT_DIR/实施总文档_最新.docx"

echo "✅ 导出完成: $EXPORT_FILE"
echo "✅ 快照: $SNAPSHOT"
echo "✅ 符号链接: $EXPORT_DIR/实施总文档_最新.docx → $(basename $EXPORT_FILE)"
