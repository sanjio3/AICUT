---
name: aicut-ending-dissolve
description: >-
  结尾溶解特效：用两层不同强度的模糊按比例混合，做出持续柔化、压暗的收尾，
  而不是一下一下的闪动。This skill should be used when the user asks for 结尾溶解 /
  结尾模糊 / 收尾柔化 / ending dissolve，或抱怨「结尾太糊」「结尾还在闪」需要调参时。
  渲染前必须回传可调参数表。
version: 0.1.0
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["结尾溶解", "结尾模糊", "收尾柔化", "ending dissolve", "结尾太糊"]
---

# 结尾溶解

片尾专用：`split=2` 拆两路，一路轻模糊并压暗、一路重模糊，再按 `keep/mix` 加权混合。两层都模糊保证了「一直糊」而不是单帧闪动，`mix` 控制重模糊那层占比。

## 何时使用

用户说出上面 `triggers` 里的词，或指出片尾需要「持续模糊收尾」「不要闪」时加载本 skill。只加载本目录。

## 怎么用

1. 所有命令都在 AICUT 仓库根目录执行（`$AICUT_ROOT`）。先跑 `python aicut.py params --effect ending-dissolve` 回传参数表。
2. 用户确认后：`python aicut.py plan --run <id> --effects ending-dissolve`（通常配合 `base` 一起轮替，只作用于尾段）。
3. `render` 后 `qa`，关注 `laplacian_var` 明显下降、`V` 略降但不塌。

## 渲染前必须回传的参数表

- `gblur_sigma` 默认 8（全局组），范围见根 `params.yaml`，决定基础模糊半径。
- `gamma` 默认 0.68，范围 0.40–1.00，压暗系数，影响 V 与 dark_pct。
- `mix` 默认 0.28，范围 0–0.60，第二层模糊占比，越高越糊，影响 motion_p90 与 laplacian_var。

## 验收

`laplacian_var` 应显著低于正片（糊）；`V` 略降但不出现大面积暗场（`dark_pct < 2%`）；连续抽帧确认是全片持续模糊，不是隔帧清晰。

## 已知坑

用 `blend all_expr` 而不是 `all_mode=screen`，后者会把 U/V 抬高染色。两层都要先 `format=yuv420p` 再混合。详见 `references/pitfalls.md`。

## 当前实现边界

参数化的双层模糊，只作用于被 `plan` 分配到该特效的镜头（尾段）。v30 的 96 帧交叉溶解序列、每 4 帧一换的连续模糊节奏未迁移——`dissolve_frames` 目前只写进 plan.json，不影响滤镜链。
