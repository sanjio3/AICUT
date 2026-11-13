---
name: aicut-manga-split
description: 漫画分格 / 分屏特效。用户说「漫画分格 / 分屏 / 不规则分格 / manga split」时启用，把镜头切成明暗交替的分格。渲染前必须回传可调参数表。触发词：漫画分格、分屏、切碎一点、不规则变换、manga split。
version: 0.1.0
triggers: ["漫画分格", "分屏", "切碎一点", "不规则变换", "manga split"]
allowed-tools: Bash, Read, Write, Edit
---

# 漫画分格

镜头级分格特效。根 `SKILL.md` 路由命中后只加载本目录。

## 渲染前必须回传的参数表

执行 `python aicut.py params --effect manga-split`，逐项回传当前值、范围、影响指标、副作用，用户确认后再渲染。

- `cells` 固定 4 不可调。0.1.0 只做规则四格，两格黑白两格彩色。
- `mono_sat` 默认 0.05，范围 0–1，影响 V 与 laplacian_var。
- `color_sat` 默认 1.40，范围 0.5–2.5，主要影响 V。
- `contrast` 默认 1.25，范围 0.9–2.0，影响 V 与 dark_pct。
- `beat_align` 默认开，由 `lib/plan.py` 消费。

## 验收

关注 `V` 是否落在 100–160、`dark_pct < 2%`，以及 `laplacian_var` 是否随 mono_sat 变化。改参数后必须跑 `diff` 回传给用户。

## 已知坑

`hstack` / `vstack` 在 2018 版 ffmpeg 上不要带 `inputs=` 参数，默认按两输入处理即可，多写参数会直接报错。crop 的四块必须是同一像素格式，否则 stack 会失败；基础链已统一为 yuv420p。分格位置固定的根因是只有一套手写多边形，v30 的解法是程序生成 8 套蒙版再逐镜挪裁切偏移，这部分尚未迁移。

## 当前实现边界

规则四格是可运行的最小实现，用来验证「说名字 → 回传参数 → 调参 → 增量重渲 → diff」这条链路。用户要「切得碎一点、不规则变换」时，本版本只能调饱和度与对比度，不能改分格形状；需要在下一阶段把 v30 的 `build_manga_assets()` 与 `build_slice_masks()` 迁进来，并新增 `mask_set`、`mask_offset_x`、`mask_offset_y` 三个旋钮。
