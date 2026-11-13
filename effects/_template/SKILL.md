---
name: aicut-<NAME>
description: TODO 一句话说明这个特效做什么，以及用户会怎么说它。渲染前必须回传可调参数表。
version: 0.1.0
triggers: ["TODO触发词1", "TODO触发词2"]
allowed-tools: Bash, Read, Write, Edit
---

# <NAME>

TODO 用两三句话说明画面效果、适用段落、需要什么素材。不要写成教程，说清楚「看到什么」即可。

## 渲染前必须回传的参数表

执行 `python aicut.py params --effect <NAME>`，把合并后的当前值、范围、影响指标、副作用逐项回传给用户。用户未表态时才用默认值，不允许先渲后报。

- TODO 参数名 默认 x，范围 a–b，影响 xxx。
- TODO 参数名 默认 y，锁定/可选，原因 xxx。

## 验收

TODO 写出这个特效该看 `qa.json` 里哪几个指标、阈值是多少。至少要写亮度类与清晰度类各一项。跑一次 `python aicut.py qa --run <id>` 把实测数字填进来。

## 已知坑

TODO 写 ffmpeg 版本限制、素材要求、容易踩的坑。没有就明确写「暂无」。已知全局限制见 `lib/doctor.py`，不要凭记忆判断某台机器支持什么滤镜。

## 当前实现边界

TODO 写清楚哪些参数还没真正生效、哪些视觉效果尚未实现、和参考片差在哪里。这一段不许留空，也不许把简化实现说成完整实现——后面的人会照着这份文件判断能不能复用。
