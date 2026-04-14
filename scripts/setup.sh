#!/usr/bin/env bash
# setup.sh - 首次使用依赖检测与安装
# Usage: bash scripts/setup.sh

set -e

echo "🔍 检测 book-hunter 依赖..."

MISSING=0

# 检测 Python3
if ! command -v python3 &>/dev/null; then
  echo "❌ python3 未安装"
  exit 1
fi

# 检测 pip 包
for pkg in requests beautifulsoup4 lxml camoufox; do
  mod="$pkg"
  # pip 包名和 import 名不一致的映射
  [ "$pkg" = "beautifulsoup4" ] && mod="bs4"
  if ! python3 -c "import $mod" &>/dev/null; then
    echo "⚠️  Python 包 $pkg 未安装"
    MISSING=1
  else
    echo "✅ $pkg"
  fi
done

if [ "$MISSING" -eq 1 ]; then
  echo ""
  echo "📦 安装缺失的 Python 依赖..."
  pip install requests beautifulsoup4 lxml camoufox
fi

# 检测 camoufox 浏览器二进制
echo ""
echo "🔍 检测 Camoufox 浏览器二进制..."
if python3 -c "from camoufox.sync_api import Camoufox; print('ok')" &>/dev/null; then
  echo "✅ Camoufox 浏览器二进制已就绪"
else
  echo "⚠️  Camoufox 浏览器二进制未下载，开始下载（约 80-150MB，可能耗时几分钟）..."
  python3 -m camoufox fetch
fi

# 最终验证
echo ""
echo "🔍 最终验证..."
python3 -c "
import requests, bs4, lxml
from camoufox.sync_api import Camoufox
print('✅ 所有 Python 依赖验证通过')
"

echo "🎉 setup 完成，可以正常使用 book-hunter"
