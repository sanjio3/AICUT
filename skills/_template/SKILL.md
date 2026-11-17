---
name: aicut-<NAME>
description: >-
  TODO 一句话说明这个特效做什么，以及用户会在什么时候需要它。
  This skill should be used when the user asks for <NAME> 相关效果，
  e.g. 用户说「TODO 触发词1」「TODO 触发词2」。渲染前必须回传可调参数表，
  用户确认后才进入渲染。
version: 0.1.0
agent_created: true
allowed-tools: Bash, Read, Write, Edit
triggers: ["TODO触发词1", "TODO触发词2"]
---

# <NAME>

TODO 用两三句话说明画面效果、适用段落、需要什么素材。不要写成教程，说清楚「看到什么」即可。

## 何时使用

用户说出上面 `triggers` 里的词，或描述的诉求与这个特效一致时加载本 skill。只加载本目录，不要通读其它 skill。

## 怎么用

1. 所有命令都在 AICUT 仓库根目录执行（`$AICUT_ROOT`）。先跑 `python aicut.py params --effect <NAME>`，把参数表逐项回传给用户（当前值、范围、影响的观测指标、副作用）。
2. 用户确认后，把特效名写进 `selection.effects`：`python aicut.py plan --run <id> --effects <NAME>`。
3. `python aicut.py render --run <id>` 出片，`python aicut.py qa --run <id>` 取指标。
4. 参数细节见 `references/params.yaml`，版本限制与验收阈值见 `references/pitfalls.md`。

## 渲染前必须回传的参数表

TODO 说明这个特效暴露哪几个旋钮，默认值、范围、各自影响什么指标。执行 `python aicut.py params --effect <NAME>` 输出合并后的当前值，逐项回传，用户未表态时才用默认值。

## 验收

TODO 写清这个特效该看 `qa.json` 里哪几个指标、阈值多少。至少写亮度类与清晰度类各一项。跑一次 `python aicut.py qa --run <id>` 把实测数字填进来。

## 已知坑

TODO 写 ffmpeg 版本限制、素材要求、容易踩的坑。没有就写「暂无」。全局限制见 `lib/doctor.py`，不要凭记忆判断某台机器支持什么滤镜。

## 当前实现边界

TODO 写清楚哪些参数还没真正生效、哪些视觉效果尚未实现、和参考片差在哪里。这一段不许留空，也不许把简化实现说成完整实现——后面的人会照着这份文件判断能不能复用。
