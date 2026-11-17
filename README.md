# AICUT

**给 AI Agent 用的卡点燃向剪辑插件。** 你说「火焰转场」，Agent 载入对应的小 skill，在渲染前把可调参数表回传给你；你调完参数，它只重渲受影响的镜头，最后回传量化指标与版本 diff。

这是一个 Skill 形态的插件，不是剪辑软件：没有前端、没有后端、没有端口、没有常驻进程。仓库根目录就是 skill 根目录，放进 Agent 的 skill 搜索路径即可工作——运行时由宿主 Agent 提供，像素由 ffmpeg 提供。

> AICUT is an agent plugin (skill-shaped, no server, no UI) that gives an AI assistant beat-synced, effect-driven AMV editing ability. Name an effect, the agent loads that effect's small self-contained skill, returns a tunable parameter table *before* rendering, renders only the affected shots, then reports a QA diff.

## 效果

![AICUT 样片关键帧](docs/demo/keyframes.jpg)

[▶ 完整样片：48 秒 / 720p / 16 MB](docs/demo/aicut-demo-48s.mp4)

这支片子是这套方法论迭代出来的样子：开场白框里嵌下一段素材做延时转场，16 秒起进漫画分格并把拟声词压到角落，结尾整段连续模糊压暗、只在拍点上偶发闪亮。

需要说清楚的是，样片出自 AICUT 之前的手工迭代版本（v30 渲染脚本），AICUT 正在把那套视觉内核逐个迁成可复用的 effect。仓库里现有三个 effect 是契约完整、可独立调用、可复现的简化实现，不是这支片子的像素级复刻——差距清单写在文末「当前状态」里。

## 一次调用长什么样

```
你    ：这段音乐剪成燃向的，加个火焰转场
Agent ：命中 fire-transition，回传 8 个旋钮（当前值 / 范围 / 影响什么）等确认
你    ：火焰暗一点，转场快一点
Agent ：plan 重排 → render 只重渲受影响的 4 个镜头 → qa → 回传指标 diff
```

对应到命令就是一条链：

```
python aicut.py catalog --say "加个火焰转场，再要一点漫画分格"
python aicut.py params  --effect fire-transition
python aicut.py plan    --run r1 --effects fire-transition,base --set fire-transition.flame_gain=2.2
python aicut.py render  --run r1
python aicut.py qa      --run r1
```

`catalog` 只负责把用户原话映射到 effect；真正决定这一片用哪几个特效的是 `selection.effects`——用户点名哪几个，就只轮替哪几个，被点名的之外不会偷偷混进来。

## 能力

**自动卡点。** `prepare` 用三频段 spectral flux（低频 30–160 Hz / 中频 160–1200 Hz / 高频 1200–7000 Hz）检测 onsets，自相关估速后用网格相位打分精修 BPM，downbeat 按 4/4 的低频能量定相位，段落边界由 RMS 与频谱质心的突变检测。只依赖 numpy 与 ffmpeg，不需要 librosa。BGM 缺失时退回等距网格加 `project.bpm_fallback`，精度降低但链路不断。

**素材自预处理。** 不需要人工挑素材、剪片段或标黑场。`prepare` 扫描素材目录，按 7 点采样算出每段素材的时长、帧率、平均亮度，再整段扫出黑场区间；文件名含「火焰 / fire / burn」的自动归到叠加素材池。产物落在 `runs/_cache/assets.json`，`Pool` 与各 effect 直接复用，不重复开文件。

**参数可归因。** 每个 skill 的 `references/params.yaml` 给每个旋钮写上 `default / min / max / step / affects / note`，`params` 打印时区分三态：带范围的滑杆、枚举、锁死值。你说的「火焰太暗」由 `attribution` 表映射到 `fire-transition.flame_gain`，而不是让 Agent 猜。

**增量渲染。** 逐镜独立出片后再 concat，失败可补渲。逐镜缓存按内容哈希命名放在 `runs/_cache/shots/`，键里含素材段、速度、effect 名与参数、ffmpeg 能力哈希、skill 代码哈希——改一个旋钮只重渲相关的镜头，改 `scripts/build.py` 会自动让对应缓存失效。

**验收指标。** 320×180 逐帧统计亮度均值、暗帧占比、过曝占比、重复帧、切点率、运动分位数、Laplacian 方差与 repeat_ratio，`gate` 按 `params.yaml` 的阈值给 PASS / WARN。WARN 只报警不回退：是不是真的坏了由人看图定，不由脚本替你决定。

## 快速开始

需要 Python 3.9+、一个可用的 ffmpeg 可执行文件，以及 `numpy`、`opencv-python`、`PyYAML`。

```
pip install -r requirements.txt
```

如果机器上有多个 Python，先确认解释器能同时导入这三个包，再往下走：

```
python -c "import yaml, numpy, cv2; print('ok')"
```

把 `.env.example` 复制成 `.env` 填本机路径，也可以直接导出同名环境变量。已存在的进程环境变量优先，`.env` 不会覆盖它，CI 注入的值不会被本机文件吃掉。

- `AICUT_FFMPEG` 指向 ffmpeg 可执行文件，默认走 PATH。
- `AICUT_VIDEOS` 指向视频素材目录，`AICUT_OVERLAYS` 指向火焰等叠加素材目录，两者可以分开。
- `AICUT_BGM` 指向 BGM 文件。`AICUT_MUSIC_JSON` 是可选兼容入口，`prepare` 自动分析出的 `music.json` 优先于它。

验证链路（没有素材也能先跑通后两步）：

```
python aicut.py prepare
python aicut.py doctor
python aicut.py params --effect fire-transition
python aicut.py plan   --run demo --effects fire-transition,base
python aicut.py render --run demo
python aicut.py qa     --run demo
python aicut.py diff   --a <run_id_1> --b <run_id_2>
```

`doctor` 打印 ffmpeg 版本、被监视的滤镜与已知版本行为差异，并把能力矩阵哈希进渲染缓存——换一台机器或换一版 ffmpeg，缓存自动失效，不会拿旧片段骗你。

`examples/make_demo_assets.py` 用 ffmpeg 的 lavfi 源生成 3 段可自由分发的合成素材，没有真实素材时也能端到端跑一遍。

## 特效

当前 3 个 effect、17 个触发词，`python aicut.py catalog` 可查。

- `fire-transition` 火焰转场，触发词「火焰转场 / 燃烧转场 / 火焰太暗 / 火焰过曝 / fire transition」。这是参考实现，7 个旋钮覆盖裁切点、起手留白、基底压暗、火焰增益、色度混合、拍点对齐与色相。
- `manga-split` 漫画分格，触发词「漫画分格 / 分屏 / 切碎一点 / 不规则变换 / manga split」。四象限错位加白色十字线。
- `ending-dissolve` 结尾溶解，触发词「结尾溶解 / 胶片转场 / 连续模糊 / 一秒四切 / 太模糊 / 看不出连续感 / ending dissolve」。双层加权模糊，用逐平面表达式混合而非 `all_mode=screen`，避免整幅染紫。

新增一个特效不碰共享文件：

```
python aicut.py new-effect my-effect
python aicut.py validate-effect my-effect      # 不跑全片，静态检查 + 用假 shot 真调一次 build()
python aicut.py catalog                        # 确认能被发现
python aicut.py install --dry-run              # 看会装到哪，不写入
python aicut.py install                        # 装到 ~/.workbuddy/skills/
```

每个特效是一个**标准 Skill**：`skills/<name>/` 下有 `SKILL.md`（原生 frontmatter + 何时使用 + 四段必写章节）、`scripts/build.py`（纯函数）、`references/params.yaml`（旋钮）与 `references/pitfalls.md`（参数表 / 验收 / 坑 / 边界）。路由由宿主读 `description` 完成，`triggers` 只是可选加速索引。加特效不用改 `lib/`，也不用改根 `SKILL.md`——多人同时开发不会在同一个文件上打架。

## 目录

- `SKILL.md` Agent 的编排入口，六步工作流与全局踩坑都在这。
- `params.yaml` 用户唯一需要改的文件：路径、全局旋钮、归因表、gate 阈值。
- `skills/<name>/` 一个特效一个标准 skill：`SKILL.md` + `scripts/build.py` + `references/params.yaml` + `references/pitfalls.md`。
- `install.py` 把 `skills/` 装到宿主扫描路径（`~/.workbuddy/skills/` 或项目级）。
- `lib/` 无状态执行内核，不面向用户。`beat.py` 自动卡点，`assets.py` 自预处理，`render.py` 缓存与拼接，`qa.py` 指标。
- `runs/<id>/` 每次出片的快照，append-only，供 diff 回放；`runs/_cache/shots/` 是跨 run 共享的片段缓存。
- `adapters/` MCP 薄适配的预留位，默认不引入任何运行时依赖。
- `tests/smoke.py` 零依赖基线（skill 可发现且无冲突、原话命中正确、全部 skill 自检、标准布局齐全、安装器能发现 skill、`selection.effects` 真限制轮替、参数覆盖优先级、源码可编译）。
- `docs/` 样片与协作说明，`examples/` 合成素材生成脚本。
- `.github/` 任务卡、PR 检查表与 CODEOWNERS，`CONTRIBUTING.md` 分工边界、分支命名与提交规范。

## 设计约束

全程用浮点秒记录时间，换算成帧只发生在渲染最后一步。每个 `scripts/build.py` 是不落盘、不启进程的纯函数：

```
build(shot, params, caps) -> (extra_inputs, filter_chain_lines)
```

基础链输入固定叫 `[g]`，额外输入从 1 开始编号，最后一行必须输出 `[out]`。路径一律由 `params["_overlays"]` / `["_assets"]` / `["_geom"]` 注入，skill 不读全局配置、不自己找文件。这条契约让每个特效可以被单测、被替换、被同学独立开发。

## 复现边界

`plan.json` + `effective.yaml` + 固定素材池种子 + ffmpeg 能力哈希 + skill 代码哈希，保证**本机**逐镜可复现：同一台机器、同一批素材、同一组参数，重跑出的是同一批镜头。

跨机器只能复现节奏与参数，不能复现像素——素材、BGM、字体与 ffmpeg 二进制都不随仓库分发，既是为了不污染许可，也是因为它们本来就该由使用者自己准备。仓库不打包这些内容，`LICENSE` 只覆盖本仓库代码，第三方许可说明见 `NOTICE`。

## 当前状态

0.3.0 把特效从「仿 SKILL.md 的自研目录」改成了**标准 Skill**：每个特效在 `skills/<name>/` 下有原生 frontmatter（`name` / `description` / `agent_created`）的 `SKILL.md`、`scripts/build.py` 与 `references/`（`params.yaml` + `pitfalls.md`），由宿主读 `description` 自动加载，`install.py` 负责装到扫描路径。叠加 0.2.0 已有的三条能力：用户点名哪几个特效就只轮替哪几个（`selection.effects` 是唯一开关）；`prepare` 自动识别 BGM 卡点与素材黑场；`validate-effect` 与 `catalog` 做提交前自检。

完整 48 秒链路实测：138 镜、104 拍点、48.04 秒，暗帧 5.3%、重复帧 1.6%、切点 4.31/s。样片级的视觉内核尚未迁移，差的部分是文字烘焙、不规则斜切蒙版、拟声字排版、96 帧交叉溶解序列与定格电光——这些目前还留在 v30 的渲染脚本里，1:1 复现是下一阶段的硬验收线。

## 参与

不需要会写代码也能参与：收集特效参考、拆解参数、跑验证、写踩坑记录都是有效分工。新人由负责人带着走一遍「clone → 分支 → 提交 → PR」，命令序列与分支规范见 `CONTRIBUTING.md`。

## 许可

代码以 `LICENSE` 为准。`NOTICE` 里列了 ffmpeg 的调用方式、`lib/beat.py` 的来源与重授权状态，以及素材不入库的原因。发布衍生作品前请自行确认第三方素材的授权。
