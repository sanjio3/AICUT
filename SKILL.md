---
name: aicut
display_name: "AICUT 卡点燃向剪辑"
description: >-
  Agent plugin that gives an AI assistant beat-synced, effects-driven video editing ability.
  Routes a user's colloquial effect name (e.g. 火焰转场, 漫画分格, 结尾溶解) to a standard
  sub-skill, returns the tunable parameter table BEFORE rendering, then renders only the
  affected shots and reports a QA diff. This skill should be used when the user asks for
  AMV / 卡点 / 燃向 / 混剪 / 转场特效, wants to adjust an effect's parameters, or wants to
  reproduce the rhythm of an existing cut.
  用卡点燃向剪辑插件给 AI 增加剪辑特效能力：说出特效名即载入对应子 skill，渲染前回传可调参数，
  调参后增量重渲并回传指标 diff。触发词：火焰转场、漫画分格、结尾溶解、卡点、燃向、AMV、混剪、调参。
description_zh: "卡点燃向剪辑插件：说特效名 → 载入子 skill → 回传参数 → 调参 → 增量重渲 → 指标 diff"
description_en: "Beat-synced effect editing plugin: name an effect, load its sub-skill, tune parameters, re-render only affected shots"
category: video
version: 0.3.0
agent_created: true
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# AICUT

AICUT 是一个 Agent 插件，不是一个应用。宿主 Agent 本身就是运行时，仓库里没有服务、没有端口、没有前后端、没有常驻进程。它提供三样东西：这份编排入口、`skills/` 下的标准特效 skill、`lib/` 下的薄执行库。

## 目录约定

```
skills/<name>/SKILL.md              标准 skill：原生 frontmatter + 何时使用 + 四段必写章节
skills/<name>/scripts/build.py      build(shot, params, caps) 纯函数，唯一的视觉实现
skills/<name>/references/params.yaml  可调旋钮（机器读）
skills/<name>/references/pitfalls.md  参数表 / 验收阈值 / 已知坑 / 实现边界（人读）
install.py                          把 skills/ 装到宿主扫描路径
```

`skills/` 是源，安装只是一份副本。`python install.py --dry-run` 先看装到哪，`python install.py` 装到 `~/.workbuddy/skills/`，`--project <dir>` 装到 `<dir>/.workbuddy/skills/`。

## 特效路由

**路由由宿主完成**：每个 skill 的 `description` 写明「何时使用」和用户会说的词，宿主读 description 判断该不该加载。`triggers` 是可选的加速索引，缺了也能从 description 兜底。

`python aicut.py catalog` 汇总可发现的 skill；`catalog --say "加个火焰转场"` 是调试用的离线模拟，用来检查 description / triggers 写得够不够清楚、有没有两个 skill 抢同一句话。**它不是运行时路由。**

命中后加载对应 `skills/<name>/SKILL.md`，只读那一个目录。名字写进 `selection.effects` 才真正生效。

## 工作流（六步，顺序不可换）

1. `python aicut.py prepare` 一键预处理：扫描视频素材生成时长、亮度与黑场索引，自动发现叠加素材，自动分析 BGM 的 BPM、拍点、downbeat 与段落边界，产物落在 `runs/_cache/`。随后 `python aicut.py doctor` 确认 ffmpeg 能力矩阵。
2. 宿主按 description 加载命中的特效 skill，把命中的名字通过 `plan --effects` 写进 `runs/<id>/params.yaml` 的 `selection.effects`。**加载 skill 不等于用上该特效**，selection 是唯一生效的开关。参数合并优先级从高到低：镜头级覆盖、skill 局部 `references/params.yaml`、全局 `params.yaml`、代码内置默认。
3. **在渲染之前**把合并后的可调参数表回传给用户，逐项给出当前值、范围、影响的观测指标、副作用提示。用户未表态时才可使用默认值。这是硬要求，不允许先渲后报。
4. 用户调参后写入 `overrides`，执行 `python aicut.py plan --run <id> --effects <名字>` 生成 `plan.json`。缓存键是 `hash(src, seg, speed, effect_id, 该 effect 的参数子集, ffmpeg 能力矩阵, 叠加素材索引, skill 代码哈希)`，跨 run 共享，只重渲命中的镜头。
5. `python aicut.py render --run <id>` 出片，`python aicut.py qa --run <id>` 得到 `qa.json` 与逐秒对照图。
6. `python aicut.py diff --a <id1> --b <id2>` 回传「改了哪几个键、指标怎么变」。gate 只报警不自动回退，主观判断留给用户。不满意回到第 3 步。

## 命令面

所有命令由宿主 Agent 用 Bash 直接调用，不启动服务。路径全部走 `params.yaml` 的 `${ENV:-default}` 展开，仓库内不硬编码任何本机绝对路径。

- `python aicut.py prepare` 自动预处理素材与 BGM，生成 `runs/_cache/assets.json` 与 `music.json`。
- `python aicut.py doctor` 输出 ffmpeg 版本与 filter 能力矩阵。
- `python aicut.py catalog [--say "..."]` 汇总可发现的 skill，或调试某句话会命中谁。
- `python aicut.py new-effect <name>` 生成标准 skill 骨架；`validate-effect --all` 自检全部 skill。
- `python aicut.py params --effect fire-transition` 回传该特效的可调参数表（第 3 步用）。
- `python aicut.py plan --run <id> --effects fire-transition,base` 只轮替点名的特效。
- `python aicut.py render --run <id>` 增量渲染并合成成片。
- `python aicut.py qa --run <id>` 出指标与 gate 判定。
- `python aicut.py diff --a <id1> --b <id2>` 回传参数与指标 diff。
- `python aicut.py install [--dry-run] [--project <dir>] [--force] [--only a,b]` 安装 skill。

## 归因表与记忆

用户口语到参数路径的映射写在 `params.yaml` 的 `attribution` 段。AI 遇到「太晃」「素材重复」「太模糊」「一下一下闪」这类反馈时先查表再改参数，不要猜。每次出片在 `runs/<id>/` 落 `params.yaml`、`plan.json`、`qa.json`、`feedback.yaml`，append-only，靠 `diff` 回放。

机器相关的踩坑分两级：全局的 ffmpeg 版本限制在 `lib/doctor.py`，单个特效的坑在各自 `references/pitfalls.md`。两者都进渲染缓存哈希，换机器时缓存自动失效。

## 已知坑（全局）

本机 2018 版 ffmpeg 构建无 `xfade`、无 `gradients`；`overlay` 无 `format` 选项；`gblur` 只收常量 sigma；`rgbashift` 无 `c` 参数；`blend all_mode=screen` 会连 U/V 一起抬高造成整幅染紫，必须写逐平面表达式；`zoompan` 会产生相同帧。完整矩阵以 `doctor` 实测为准，不要凭记忆判断。

## 当前实现边界

三个内置 skill（fire-transition / manga-split / ending-dissolve）是契约完整、可复现的简化实现，不是 v30 的像素级复刻。v30 的文字烘焙、不规则蒙版、拟声字、96 帧交叉溶解序列尚未迁移，各自 `references/pitfalls.md` 的「当前实现边界」写明了缺口。
