---
name: aicut-fire-transition
description: >-
  火焰转场特效：把火焰叠加素材按拍点吸附到镜头切点上，同时压暗底图让火焰成为视觉焦点。
  This skill should be used when the user asks for 火焰转场 / 燃烧转场 / fire transition，
  或抱怨「火焰太暗」「火焰过曝」需要调参时。渲染前必须回传可调参数表，用户确认后才渲染。
version: 0.1.0
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["火焰转场", "燃烧转场", "fire transition", "火焰太暗", "火焰过曝"]
---

# 火焰转场

镜头级的转场特效：取一段火焰素材循环播放，与镜头画面做逐平面加权混合，底图按系数压暗，火焰亮度按增益抬高，切点由 `lib/plan.py` 吸附到最近拍点。

## 何时使用

用户说出上面 `triggers` 里的词，或要求「切点处加火」「燃烧感转场」时加载本 skill。只加载本目录，不要通读其它 skill。

## 怎么用

1. 所有命令都在 AICUT 仓库根目录执行（`$AICUT_ROOT`）。先跑 `python aicut.py params --effect fire-transition`，把参数表逐项回传给用户（当前值、范围、影响指标、副作用）。
2. 用户确认后写入生效开关：`python aicut.py plan --run <id> --effects fire-transition`。
3. `python aicut.py render --run <id>` 出片，`python aicut.py qa --run <id>` 取指标。
4. 参数含义与验收阈值见 `references/pitfalls.md`，旋钮定义见 `references/params.yaml`。

## 渲染前必须回传的参数表

执行 `python aicut.py params --effect fire-transition` 拿到合并后的当前值，逐项回传：当前值、范围、影响的观测指标、副作用。用户未明确表态时才使用默认值。

- `clip` 默认 fire01，可选 fire01 / fire02，决定火焰形状。
- `trim_start` 默认 0.55s，范围 0–1.5s，太早取到黑场。
- `base_dim` 默认 0.68，范围 0.40–1.00，压暗底图，主要影响 V 与 dark_pct。
- `flame_gain` 默认 1.95，范围 0.80–2.60，主要影响 bright_pct，超过 2.4 容易过曝。
- `chroma_mix` 默认 0.28，只改 U/V 平面，不改亮度。
- `beat_align` 默认开，由 `lib/plan.py` 消费，关掉后切点不再吸附拍点。
- `hue` 锁定 6° 不可调。

参数优先级从高到低是镜头级覆盖、本目录 `references/params.yaml`、全局 `params.yaml`、代码内置默认。调 `flame_gain` 只会让 `effect == "fire-transition"` 的镜头缓存失效，其余镜头直接复用。

## 验收

渲完执行 `python aicut.py qa --run <id>`，本特效关注 `bright_pct < 8%`、`dark_pct < 2%`、`V` 在 100–160 之间；全局 gate 另见根 `params.yaml`。改参数后用 `python aicut.py diff --a <id1> --b <id2>` 回传「改了哪几个键、指标怎么变」。

## 已知坑

详见 `references/pitfalls.md`。要点：`blend all_mode=screen` 会连 U/V 一起抬高，整幅画面染紫，必须用逐平面 `c0_expr` 改亮度、`c1_expr`/`c2_expr` 改色度；火焰镜头不要做色相旋转，橙红会被染成紫色；底层素材用 `-stream_loop -1` 兜底，因为火焰 mov 往往短于镜头时长。

## 当前实现边界

本 skill 是 0.1.0 的可运行实现：逐平面叠加、素材轮替、参数化完整。v30 里的 HUD 扫描光带、霓虹网格叠加、不规则蒙版尚未迁移。缺 overlays 素材时 `scripts/build.py` 会自动降级成轻度提亮，保证链路不中断，并在 QA 的 V 上体现出来。
