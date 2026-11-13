---
name: aicut-ending-dissolve
description: 结尾连续模糊溶解 / 胶片转场。用户说「结尾溶解 / 胶片转场 / 连续模糊 / 太模糊 / 一下一下闪」时启用。渲染前必须回传可调参数表。触发词：结尾溶解、胶片转场、连续模糊、一秒四切、太模糊、看不出连续感。
version: 0.1.0
triggers: ["结尾溶解", "胶片转场", "连续模糊", "一秒四切", "太模糊", "看不出连续感", "ending dissolve"]
allowed-tools: Bash, Read, Write, Edit
---

# 结尾溶解

结尾段落专用的连续模糊特效。根 `SKILL.md` 路由命中后只加载本目录。

## 渲染前必须回传的参数表

执行 `python aicut.py params --effect ending-dissolve`，逐项回传当前值、范围、影响指标、副作用。

- `gblur_sigma` 默认 8，范围 0–20，定义在全局 `params.yaml`。sigma=20 时「太模糊看不出是什么」，用 `laplacian_var` 复核。
- `dissolve_frames` 默认 96，范围 24–192，定义在全局。硬切加模糊不等于连续变换，96 帧交叉溶解曾把帧差 p90 从 45.7 降到 15.7。
- `gamma` 默认 0.68，范围 0.40–1.00，影响 V 与 dark_pct。
- `mix` 默认 0.28，范围 0–0.60，影响 motion_p90 与 laplacian_var。

用户反馈「有点太模糊了」时先查根 `params.yaml` 的归因表，命中 `ending-dissolve.gblur_sigma` 再改，不要凭感觉动 `mix`。改完必须跑 `diff` 回传指标变化。

## 验收

关注 `cut_rate` 是否接近 0（结尾不应有硬切）、`motion_p90` 是否稳定、`laplacian_var` 是否还读得出内容。gate 只报警不自动回退。

## 已知坑

2018 版 ffmpeg 的 `gblur` 只收常量 sigma，不能写时间表达式。缺 `xfade`，所以连续溶解必须靠预生成序列或双层加权混合，不能用现成转场滤镜。`blend all_mode=screen` 会连色度抬高造成整幅染紫，这里用的是线性加权 `all_expr='A*0.72+B*0.28'`，不会染色。`zoompan` 会产生相同帧，推镜走 `scale+crop` 表达式。

## 当前实现边界

0.1.0 用「双层不同 sigma 的常驻模糊 + 线性加权 + 基础链慢推」近似连续模糊变换，链路可跑、参数可调、指标可观测。v30 真正的 96 帧交叉溶解是 numpy 预生成 96 张 `dis_%03d.png` 再逐帧喂给 ffmpeg，尚未迁移；`dissolve_frames` 这个旋钮在当前版本只记录到 `plan.json`，不直接影响滤镜链。迁移后该旋钮才会真正生效，届时需同步补上 `references/` 里的序列生成说明。
