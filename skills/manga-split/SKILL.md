---
name: aicut-manga-split
description: >-
  漫画分格特效：把一个镜头切成四格错位画面并画白色十字分格线，两格去饱和、两格高饱和，
  形成漫画分镜的对比感。This skill should be used when the user asks for 漫画分格 / 漫画分屏 /
  分镜 / manga split，或要求「画面切成几块」「漫画感」时。渲染前必须回传可调参数表。
version: 0.1.0
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["漫画分格", "漫画分屏", "分镜", "manga split", "漫画感"]
---

# 漫画分格

规则四格分屏：`split=4` 拆成四路，每格裁切区域彼此错位（不是按原象限拼回原位，否则几何完全还原、肉眼看不出分屏），两格降饱和成黑白、两格提饱和，最后叠白色十字分格线。

## 何时使用

用户说出上面 `triggers` 里的词，或要求「把画面切块」「漫画分镜感」时加载本 skill。只加载本目录。

## 怎么用

1. 所有命令都在 AICUT 仓库根目录执行（`$AICUT_ROOT`）。先跑 `python aicut.py params --effect manga-split`，把参数表回传给用户。
2. 用户确认后：`python aicut.py plan --run <id> --effects manga-split`。
3. `python aicut.py render --run <id>` 出片，`python aicut.py qa --run <id>` 取指标。
4. 细节见 `references/pitfalls.md`。

## 渲染前必须回传的参数表

- `cells` 锁定 4，当前实现只支持规则四格。
- `mono_sat` 默认 0.05，范围 0–1，黑白格饱和度，影响 V 与 laplacian_var。
- `color_sat` 默认 1.40，范围 0.5–2.5，彩色格饱和度，影响 V。
- `contrast` 默认 1.25，范围 0.9–2.0，统一对比度，影响 V 与 dark_pct。
- `beat_align` 默认开，由 `lib/plan.py` 消费。

## 验收

关注 `V` 不因双色对比剧烈漂移、`dark_pct < 2%`（黑白格压太狠会爆）、`laplacian_var` 因分格线抬高属正常。分格线必须可见，抽一帧目视确认。

## 已知坑

`split=4` 后四路必须各自 `crop` 到 `w//2 x h//2` 再 `hstack`/`vstack`，否则尺寸不匹配。错位量不能超过半格，否则出现边缘黑边。详见 `references/pitfalls.md`。

## 当前实现边界

只支持规则四格。v30 的不规则斜切蒙版、随机分格形状未迁移——那需要预生成蒙版序列或 `maskedmerge` 配合动态蒙版，属下一阶段。`cells` 锁死为 4 是这一限制的直接体现。
