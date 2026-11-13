---
name: aicut
display_name: "AICUT 卡点燃向剪辑"
description: >-
  Agent plugin that gives an AI assistant beat-synced, effects-driven video editing ability.
  Routes a user's colloquial effect name (e.g. 火焰转场, 漫画分格, 结尾溶解) to a small self-contained
  effect skill, returns the tunable parameter table BEFORE rendering, then renders only the affected
  shots and reports a QA diff. Use when the user asks for AMV / 卡点 / 燃向 / 混剪 / 转场特效,
  wants to adjust an effect's parameters, or wants to reproduce the rhythm of an existing cut.
  用卡点燃向剪辑插件给 AI 增加剪辑特效能力：说出特效名即载入对应小 skill，渲染前回传可调参数，
  调参后增量重渲并回传指标 diff。触发词：火焰转场、漫画分格、结尾溶解、卡点、燃向、AMV、混剪、调参。
description_zh: "卡点燃向剪辑插件：说特效名 → 回传参数 → 调参 → 增量重渲 → 指标 diff"
description_en: "Beat-synced effect editing plugin: name an effect, tune its parameters, re-render only affected shots"
category: video
version: 0.2.0
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# AICUT

AICUT 是一个 Agent 插件，不是一个应用。宿主 Agent 本身就是运行时，仓库里没有服务、没有端口、没有前后端、没有常驻进程。它只提供三样东西：这份入口文档、`effects/` 下的能力单元、`lib/` 下的薄执行库。

## 调用前先判断任务范围

用户说出某个特效名时，只加载那一个 `effects/<name>/SKILL.md`，不要通读整个仓库。用户要调整上一次的参数时，直接读 `runs/<id>/params.yaml` 与 `runs/<id>/qa.json`，不必重新分析音乐或重建全部镜头。用户要新增特效时，复制 `effects/fire-transition/` 三件套改名，并在下面的路由表加一行。

## 特效路由表

路由表**不在这份文件里**。每个 effect 在自己 `SKILL.md` frontmatter 的 `triggers` 字段声明触发词，由 `lib/catalog.py` 自动汇总。执行 `python aicut.py catalog` 查看全表，执行 `python aicut.py catalog --say "加个火焰转场"` 查出这句话命中哪些 effect。

这样多人并行新增特效时，每个人只改自己目录里的一个字段，不会在共享文件上冲突。新增 effect 既不需要改 `lib/`，也不需要改本文件。命中结果交给 `plan --effects` 写进 `selection.effects`，那是唯一生效开关。触发词重复会在 `catalog` 里报 CONFLICTS，`validate-effect` 也会拦下。

卡点 / 节奏 / beat sync 属于编排能力而不是特效，走 `lib/music.py` 与 `lib/plan.py`。路由粒度按「用户会说的词」切，不按 ffmpeg filter 切。

## 工作流（六步，顺序不可换）

1. 执行 `python aicut.py prepare` 一键预处理：自动扫描视频素材生成时长、亮度与黑场索引，自动发现叠加素材，自动分析 BGM 的 BPM、拍点、downbeat 与段落边界，产物落在 `runs/_cache/`。用户不需要手工提供 music.json，也不需要把叠加素材改成固定文件名。随后执行 `python aicut.py doctor` 确认 ffmpeg 能力矩阵。
2. 命中路由表后，把命中的 effect 名列表通过 `plan --effects` 写进 `runs/<id>/params.yaml` 的 `selection.effects`。**加载子 skill 不等于用上该特效**，selection 是唯一生效的开关，未列入的特效不会进入轮替表。然后加载对应子 skill 读局部默认值，合并优先级从高到低是镜头级覆盖、effect 局部值、全局 `params.yaml`、代码内置默认。
3. **在渲染之前**把合并后的可调参数表回传给用户，逐项给出当前值、范围、影响的观测指标、副作用提示。用户未表态时才可使用默认值。这是硬要求，不允许先渲后报。
4. 用户调参后写入 `overrides`，执行 `python aicut.py plan --run <id> --effects <命中的名字>` 生成 `plan.json`。缓存键是 `hash(src, seg, speed, effect_id, 该 effect 的参数子集, ffmpeg 能力矩阵, 叠加素材索引)`，跨 run 共享，只重渲命中的镜头。
5. 执行 `python aicut.py render --run <id>` 出片，再执行 `python aicut.py qa --run <id>` 得到 `qa.json` 与逐秒对照图。
6. 执行 `python aicut.py diff --a <id1> --b <id2>` 回传「改了哪几个键、指标怎么变」。gate 只报警不自动回退，主观判断留给用户。不满意回到第 3 步。

## 命令面

所有命令由宿主 Agent 用 Bash 直接调用，不启动服务。路径全部走 `params.yaml` 的 `${ENV:-default}` 展开，仓库内不硬编码任何本机绝对路径。

- `python aicut.py prepare` 自动预处理素材与 BGM，生成 `runs/_cache/assets.json` 与 `music.json`。
- `python aicut.py doctor` 输出 ffmpeg 版本与 filter 能力矩阵。
- `python aicut.py catalog [--say "加个火焰转场"]` 汇总触发词路由，或查出用户这句话命中哪些 effect（第 2 步用）。
- `python aicut.py new-effect <name>` 生成新特效三件套；`python aicut.py validate-effect --all` 不跑全片即可自检全部特效。
- `python aicut.py params --effect fire-transition` 回传该特效的可调参数表（第 3 步用）。
- `python aicut.py plan --run <id> --effects fire-transition,base` 只轮替用户点名的特效，生成 `plan.json`。
- `python aicut.py render --run <id>` 增量渲染并合成成片。
- `python aicut.py qa --run <id>` 出指标与 gate 判定。
- `python aicut.py diff --a <id1> --b <id2>` 回传参数与指标 diff。

## 归因表与记忆

用户口语到参数路径的映射写在 `params.yaml` 的 `attribution` 段。AI 遇到「太晃」「素材重复」「太模糊」「一下一下闪」这类反馈时先查表再改参数，不要猜。每次出片在 `runs/<id>/` 落 `params.yaml`、`plan.json`、`qa.json`、`feedback.yaml`，append-only，靠 `diff` 回放，不靠重读历史日志。

机器相关的踩坑分两级：全局的 ffmpeg 版本限制在 `lib/doctor.py`，单个特效的坑在各自 `SKILL.md` 的「已知坑」段。两者都进渲染缓存哈希，换机器时缓存自动失效。

## 已知坑（全局）

本机 2018 版 ffmpeg 构建无 `xfade`、无 `gradients`；`overlay` 无 `format` 选项；`gblur` 只收常量 sigma；`rgbashift` 无 `c` 参数，只有 `rh/rv/gh/gv/bh/bv/ah/av/edge`；`blend all_mode=screen` 会连 U/V 一起抬高造成整幅染紫，必须写逐平面表达式；`zoompan` 会产生相同帧。`maskedmerge`、`alphamerge`、`displace` 可用。完整矩阵以 `doctor` 实测为准，不要凭记忆判断。
