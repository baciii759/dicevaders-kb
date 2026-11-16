#!/usr/bin/env python3
"""从游戏 sprite 图集切出每个单位/神器/专长/Boss技能/指挥官/法术的模板图。

数据来源：dicevader-wiki.vercel.app（从游戏安装文件提取的图集与坐标）。
运行：python3 crop_atlas.py [--atlas-dir raw_atlas] [--out assets]
生成 assets/{units,artifacts,perks,pilot_abilities,specials,spells,commanders,pilots,keywords}/*.png + manifest.json
游戏更新后重跑本脚本即可刷新模板库。
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("缺少 Pillow：pip install pillow")

BASE = Path(__file__).resolve().parent
KB = BASE.parent

ATLASES = {
    "icons":      {"src": "icons.webp",      "size": (112, 112), "cols": 20},
    "units":      {"src": "units.webp",      "size": (112, 112), "cols": 12},
    "commanders": {"src": "commanders.webp", "size": (320, 400), "cols": 5},
    "pilots":     {"src": "pilots.webp",     "size": (256, 192), "cols": 4},
}

# 关键词 -> icons.webp 索引（game.js kwIcon）
KEYWORDS = {
    "Attack": 0, "Budge": 1, "Chrono": 2, "MiniDice": 3, "DicePower": 4,
    "Shield": 5, "Shock": 6, "Charge": 7, "React": 8, "Target": 9,
    "ShopToken": 10, "Arrow": 11, "Doom": 12, "Power": 13, "Rarity": 14, "Heat": 15,
}

# kind -> 输出子目录
KIND_DIR = {
    "artifact": "artifacts",
    "perk": "perks",
    "starter": "perks",      # 起始专长并入 perks
    "pilot": "pilot_abilities",
    "special": "specials",
    # constellation 无图标，跳过
}


def crop(atlas_img, index, cols, size):
    w, h = size
    col, row = index % cols, index // cols
    return atlas_img.crop((col * w, row * h, col * w + w, row * h + h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas-dir", default=str(BASE / "raw_atlas"))
    ap.add_argument("--out", default=str(BASE / "assets"))
    ap.add_argument("--kb-json", default=str(KB / "dicevaders_data.json"))
    args = ap.parse_args()

    data = json.load(open(args.kb_json, encoding="utf-8"))
    out = Path(args.out)
    manifest = {"atlas_meta": ATLASES, "items": []}

    def load(name):
        p = Path(args.atlas_dir) / ATLASES[name]["src"]
        if not p.exists():
            sys.exit(f"缺少图集 {p}（先下载，见 vision/README.md）")
        return Image.open(p).convert("RGBA")

    atlases = {n: load(n) for n in ATLASES}

    def save(category, key, atlas_name, index):
        meta = ATLASES[atlas_name]
        img = crop(atlases[atlas_name], index, meta["cols"], meta["size"])
        d = out / category
        d.mkdir(parents=True, exist_ok=True)
        img.save(d / f"{key}.png")

    def add(category, key, en, zh, atlas_name, index, kind=""):
        if index is None:
            return
        save(category, key, atlas_name, index)
        manifest["items"].append({
            "category": category, "key": key, "en": en, "zh": zh, "kind": kind,
            "atlas": atlas_name, "index": index, "file": f"{category}/{key}.png",
        })

    # 单位 -> units.webp
    for u in data["units"]:
        add("units", u["key"], u["en"], u["zh"], "units", u["icon"])

    # 神器/专长/起始专长/Boss技能/特殊 -> icons.webp（按 kind 归类）
    for a in data["artifacts"]:
        cat = KIND_DIR.get(a["kind"])
        if cat is None or a.get("icon") is None:
            continue  # 星座等无图标实体
        add(cat, a["key"], a["en"], a["zh"], "icons", a["icon"], a["kind"])

    # 法术 -> icons.webp
    for s in data["spells"]:
        add("spells", s["k"], s["en"], s["zh"], "icons", s.get("ic"))

    # 指挥官 -> commanders.webp（index = art）
    for c in data["commanders"]:
        add("commanders", c["k"], c["name"]["en"], c["name"]["zh"], "commanders", c.get("art"))

    # Boss(驾驶员) 立绘 -> pilots.webp（index = portrait）
    for p in data["pilots"]:
        add("pilots", p["k"], p["name"], p["name"], "pilots", p.get("portrait"))

    # 关键词图标 -> icons.webp
    for name, index in KEYWORDS.items():
        add("keywords", name, name, name, "icons", index)

    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"生成 {len(manifest['items'])} 张模板 → {out}/")
    for c in ["units", "artifacts", "perks", "pilot_abilities", "specials",
              "spells", "commanders", "pilots", "keywords"]:
        d = out / c
        n = len(list(d.glob("*.png"))) if d.exists() else 0
        print(f"  {c:16s}: {n:3d} 张")


if __name__ == "__main__":
    main()
