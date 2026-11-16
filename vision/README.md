# vision — 骰之侵略者截图识别模块

让自动化 Agent「看得懂」游戏截图：从截图识别棋盘上的单位/神器/专长/Boss技能，结合知识库输出结构化棋盘状态（JSON），供下游 LLM/规则引擎做决策。

## 目录结构

```
vision/
├── download_atlas.sh   # 下载游戏 sprite 图集（4 张 webp）
├── crop_atlas.py       # 从图集切出 380 张模板图 + manifest.json
├── matcher.py          # 模板匹配（numpy FFT 的 ZNCC，无需 OpenCV）
├── ocr.py              # 数字/文字 OCR 接口（pytesseract 或接视觉模型）
├── state.py            # 状态解析：匹配 + 归列 + 知识库 → BoardState JSON
├── capture.py          # 跨平台截图
├── requirements.txt    # 依赖：numpy + Pillow（OCR 可选）
├── raw_atlas/          # 下载的图集（不入库）
└── assets/             # 生成的模板库 + manifest.json
    ├── units/          # 84 个单位
    ├── artifacts/      # 151 个神器
    ├── perks/          # 64 个专长（含 10 起始专长）
    ├── pilot_abilities/# 20 个 Boss 技能
    ├── spells/         # 17 个商店法术
    ├── commanders/     # 10 名指挥官立绘
    ├── pilots/         # 16 名 Boss 立绘
    ├── keywords/       # 16 个关键词图标
    └── manifest.json   # 键 → 模板路径/中英文名/图标索引
```

## 快速开始

```bash
cd vision
# 1. 安装依赖（用项目自带 Python 或 venv）
#    pip install -r requirements.txt
# 2. 下载图集 + 生成模板库（图集和模板库已生成好，可跳过）
bash download_atlas.sh
python3 crop_atlas.py
```

## 用模板匹配识别单位

```python
from vision.matcher import Matcher

m = Matcher().load_manifest("vision/assets/manifest.json")

# 匹配某类别（units/artifacts/perks/pilot_abilities/spells/commanders/pilots）
hits = m.match_category("units", "screenshot.png", threshold=0.7)
for h in hits:
    print(f"[{h.score:.3f}] {h.zh}({h.en}) @({h.x},{h.y}) {h.w}x{h.h}")

# 匹配单个模板，拿最佳位置
r = m.match_one("screenshot.png", "vision/assets/units/Migo.png")
# r = (score, x, y, w, h, scale) 或 None
```

## 解析完整棋盘状态

```python
from vision.state import parse_screenshot

st = parse_screenshot("screenshot.png")   # 默认匹配 units/artifacts/perks/pilot_abilities/commanders/pilots
print(st.to_dict())
# -> {"units": [{"key","en","zh","x","y","column",...}], "artifacts": [...], ...}
```

`BoardState` 的数值字段（`resources`/`target`/`dice`）留空，需要 OCR 或视觉模型补全：

```python
from vision.ocr import OCR
ocr = OCR()                          # 用 pytesseract（需系统装 tesseract）
num = ocr.read_int(crop_of_score)    # 读目标分数/力量/货币

# 或接本地/远程视觉模型读数字（对游戏 UI 更稳，推荐）：
ocr = OCR(reader=lambda img: my_vlm(img))  # my_vlm 返回字符串
```

## 校准 UI 缩放（重要）

模板是 112×112，但游戏实际渲染尺寸随分辨率变化。**首次使用时先校准**：

1. 截一张图，找画面里一个确定的单位（比如米戈）。
2. 用宽尺度范围匹配它，找到最佳 scale：
   ```python
   r = m.match_one("shot.png", "vision/assets/units/Migo.png", scale_range=(0.3, 3.0, 15))
   best_scale = r[5]
   ```
3. 之后把 scale_range 收窄成单点或小范围（如 `(best_scale*0.9, best_scale*1.1, 3)`），速度大幅提升。

## 性能

- 纯 numpy FFT，单模板单尺度 ≈ 0.2s；84 个单位 × 4 尺度 ≈ 30s（float64 精度优先）。
- 校准后单尺度匹配 84 个单位 ≈ 8s。
- **要实时（<1s）**：换 OpenCV（`cv2.matchTemplate` 是 C 实现，快一个数量级）。本模块不依赖 OpenCV，但接口已按「模板 + 阈值 → 命中」设计，替换 `_zncc` 即可，或直接 `pip install opencv-python` 后用 `cv2.matchTemplate` 重写 matcher 核心。

## 如何接进 Agent

1. `capture.py` 截图 → `state.py` 解析出 `BoardState` JSON（单位/神器/专长已识别，坐标已归列）。
2. OCR/视觉模型补全数字（目标分、资源、骰子点数）。
3. 把 `BoardState` + 知识库按需检索片段（`../dicevaders_data.json`）喂给 LLM，输出下一步动作（见 `../07_自动化Agent指南.md`）。

## 数据来源与更新

图集与坐标提取自 [dicevader-wiki.vercel.app](https://dicevader-wiki.vercel.app)（该站数据由工具从游戏安装文件 GameAssembly.dll 提取）。游戏更新后：

1. 重跑 `bash download_atlas.sh && python3 crop_atlas.py` 刷新模板。
2. 若知识库 `dicevaders_data.json` 也更新，crop_atlas 会自动按新数据重新切图。

## 依赖

- 必需：`numpy`、`Pillow`（项目自带运行时已含）。
- 可选：`pytesseract`（OCR，需系统装 Tesseract），或自行接视觉模型。
