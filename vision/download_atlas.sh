#!/usr/bin/env bash
# 下载游戏 sprite 图集（从 dicevader-wiki.vercel.app）
set -e
cd "$(dirname "$0")"
mkdir -p raw_atlas
for f in icons units commanders pilots; do
  echo "下载 $f.webp ..."
  curl -s -L -A "Mozilla/5.0" "https://dicevader-wiki.vercel.app/img/$f.webp" -o "raw_atlas/$f.webp"
done
echo "完成。运行 python3 crop_atlas.py 生成模板库。"
