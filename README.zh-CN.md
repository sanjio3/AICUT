# AICUT

**给 AI Agent 用的卡点燃向剪辑插件。**

你说「加个火焰转场」，Agent 载入对应特效的小 skill，**在渲染前先问你打算怎么剪**，回传可调参数表；你回答之后，它只重渲受影响的镜头，最后回传量化指标与版本 diff。

[English documentation](README.md)

AICUT 是一个 Skill 形态的插件，不是剪辑软件：没有前端、没有后端、没有端口、没有常驻进程。仓库根目录就是 skill 根目录，放进 Agent 的 skill 搜索路径即可工作——运行时由宿主 Agent 提供，像素由 ffmpeg 提供。

> AICUT 会询问用户想怎么剪，确认后才渲染。它给 AI 增加了卡点燃向剪辑能力：说出特效名即载入对应 skill，回传参数表，渲染前询问，确认后只重渲受影响的镜头，再回传指标 diff。

## 效果

![AICUT 样片关键帧](docs/demo/keyframes.jpg)

[▶ 完整样片：48 秒 / 720p / 16 MB](docs/demo/aicut-demo-48s.mp4)

这支片子是这套方法论迭代出来的样子：开场白框里嵌下一段素材做延时转场，16 秒起进漫画分格并把拟声词压到角落，结尾整段连续模糊压暗、只在拍点上偶发闪亮。

需要说清楚的是，样片出自 AICUT 之前的手工迭代版本（v30 渲染脚本），AICUT 正在把那套视觉内核逐个迁成可复用的 effect。仓库里现有三个 effect 是契约完整、可独立调用、可复现的简化实现，不是这支片子的像素级复刻——差距清单写在文末「当前状态」里。

## 一次调用长什么样

```
你    ：这段音乐剪成燃向的，加个火焰转场
Agent ：命中 fire-transition，回传 8 个旋钮（当前值 / 范围 / 影响什么），
        并问：用哪几个特效、多长、跟音乐的哪一段
你    ：火焰暗一点，转场快一点
Agent ：plan 重排 → confirm 记录你的决定 → render 只重渲受影响的 4 个镜头
        → qa → 回传指标 diff
```

对应到命令就是一条链：

```
python aicut.py catalog --say "加个火焰转场，再要一点漫画分格"
python aicut.py params  --effect fire-transition
python aicut.py plan    --run r1 --effects fire-transition,base --set fire-transition.flame_gain=2.2
python aicut.py confirm --run r1 --hash <plan 输出的哈希>
python aicut.py render  --run r1
python aicut.py qa      --run r1
```

`catalog` 只负责把用户原话映射到 effect；真正决定这一片用哪几个特效的是 `selection.effects`——用户点名哪几个，就只轮替哪几个，被点名的之外不会偷偷混进来。

**AICUT 在你确认之前不会渲染。** `render` 会拒绝执行没有确认记录、或哈希与当前计划对不上的渲染。Agent 跳不过这一步——它得自己编一个哈希，而编出来的哈希和磁盘上的计划对不上。

## 能力

**自动卡点。** `prepare` 用三频段 spectral flux（低频 30–160 Hz / 中频 160–1200 Hz / 高频 1200–7000 Hz）检测 onsets，自相关估速后用网格相位打分精修 BPM，downbeat 按 4/4 的低频能量定相位，段落边界由 RMS 与频谱质心的突变检测。只依赖 numpy 与 ffmpeg，不需要 librosa。BGM 缺失时退回等距网格加 `project.bpm_fallback`，精度降低但链路不断。

**素材自预处理。** 不需要人工挑素材、剪片段或标黑场。`prepare` 扫描素材目录，按 7 点采样算出每段素材的时长、帧率、平均亮度，再整段扫出黑场区间；叠加素材自动发现。产物落在 `runs/_cache/assets.json`，`Pool` 与各 effect 直接复用，不重复开文件。

**参数可归因。** 每个旋钮声明 `default / min / max / step / affects / note`，`params` 打印时区分三态：带范围的滑杆、枚举、锁死值。你说的「火焰太暗」由 `attribution` 表映射到 `fire-transition.flame_gain`，而不是让 Agent 猜。这张表中英文都给，中英文用户都命中。

**增量渲染。** 逐镜独立出片后再 concat，失败可补渲。逐镜缓存按内容哈希命名放在 `runs/_cache/shots/`，键里含素材段、速度、effect 名与参数、ffmpeg 能力哈希、skill 代码哈希——改一个旋钮只重渲相关的镜头。

**验收指标。** 320×180 逐帧统计亮度均值、暗帧占比、过曝占比、重复帧、切点率、运动分位数、Laplacian 方差与 repeat_ratio，`gate` 按 `params.yaml` 的阈值给 PASS / WARN。WARN 只报警不回退：是不是真的坏了由人看图定，不由脚本替你决定。

## 快速开始

```bash
git clone https://github.com/sanjio3/AICUT.git
cd AICUT
python -m pip install -r requirements.txt
python aicut.py install          # 把 skill 装进 ~/.workbuddy/skills
```

只需要 Python 3.9 以上和一个在 `PATH` 上的 ffmpeg（或设 `AICUT_FFMPEG`）。**不需要准备素材**：素材目录为空时 `prepare` 会自动生成合成演示片段，第一条命令就有画面看。

要用自己的素材，把 `params.yaml` 指过去或导出环境变量：

| 环境变量 | 指向 |
|---|---|
| `AICUT_FFMPEG` | ffmpeg 可执行文件 |
| `AICUT_VIDEOS` | 视频素材目录 |
| `AICUT_OVERLAYS` | 叠加素材目录（例如火焰） |
| `AICUT_BGM` | 背景音乐文件 |
| `AICUT_MUSIC_JSON` | 已分析好的 music JSON（可选） |

然后跑流水线：

```bash
python aicut.py prepare
python aicut.py plan --run mycut --effects fire-transition,base --duration 6
python aicut.py confirm --run mycut --hash <plan 输出的哈希>
python aicut.py render --run mycut
python aicut.py qa --run mycut
```

## 特效清单

| Skill | 效果 | 触发词 |
|---|---|---|
| `fire-transition` | 火焰叠加吸附拍点，底图压暗 | 火焰转场、燃烧转场、fire transition、fire wipe |
| `manga-split` | 四格错位漫画分屏加白色十字线 | 漫画分格、漫画分屏、分镜、manga split、comic panel split |
| `ending-dissolve` | 两层模糊混合，收尾持续柔化 | 结尾溶解、结尾模糊、ending dissolve、soft fade out |

每个特效是一个标准 skill：

```
skills/<name>/
├── SKILL.md                frontmatter、何时使用、必写章节
├── scripts/build.py        build(shot, params, caps) 纯函数
└── references/
    ├── params.yaml         可调旋钮（机器读）
    └── pitfalls.md         参数表、验收阈值、已知坑、实现边界
```

路由由宿主读各 skill 的 `description` 完成，`triggers` 只是可选加速索引。

新增一个特效：

```bash
python aicut.py new-effect my-effect
python aicut.py validate-effect my-effect   # 契约自检，不跑全片
python aicut.py catalog                      # 确认能被发现
python aicut.py package --effect my-effect   # 产出可分发的 zip
```

## 目录

- `SKILL.md` 唯一入口：工作流、命令面、全局踩坑。
- `params.yaml` 用户唯一需要改的文件：路径、全局旋钮、归因表、gate 阈值。
- `skills/<name>/` 一个特效一个标准 skill。
- `install.py` 把 `skills/` 装进宿主扫描路径。
- `lib/` 无状态内核：`beat.py` 卡点、`assets.py` 预处理、`plan.py` 决策、`render.py` 渲染与缓存、`qa.py` 指标、`confirm.py` 渲染门禁、`package.py` 打包。
- `runs/<id>/` 每次出片的快照，append-only，供 diff 回放；`runs/_cache/shots/` 是跨 run 共享的片段缓存。
- `tests/smoke.py` 零依赖基线，不需要 pytest、素材与 ffmpeg。
- `examples/make_demo_assets.py` 生成合成演示素材。
- `.github/` issue 与 PR 模板、CODEOWNERS、CI。

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

0.4.0 把特效改成标准 skill，并把对话放回流程里：

- 每个特效都是标准 skill，原生 frontmatter + `scripts/` + `references/`，由宿主按 description 加载。
- 渲染受确认门禁约束，确认记录带哈希且与计划一致，Agent 没法悄悄产出没人要的视频。
- 全新 clone 不需要任何素材也能出结果：`prepare` 自动生成合成演示片段。
- 内置提示词、CLI 输出与文档全部英文；中文触发词保留，中文用户同样命中。
- `package` 为每个 skill 产出可上架的 zip，CI 在每个 PR 上跑冒烟测试、契约校验与打包。

完整 48 秒链路实测：138 镜、104 拍点、48.04 秒，暗帧 5.3%、重复帧 1.6%、切点 4.31/s。样片级的视觉内核尚未迁移：文字烘焙、不规则斜切蒙版、拟声字排版、96 帧交叉溶解序列与定格电光仍留在旧渲染脚本里，1:1 复现是下一阶段的硬验收线。

## 参与

不需要会写代码也能参与：收集特效参考、拆解参数、跑验证、写踩坑记录都是有效分工。项目以 PR 方式协作，`main` 只接受 PR，每个改动都要过 CI。

分工边界、分支命名与提交命令序列见 `CONTRIBUTING.md`。

## 许可

代码以 `LICENSE` 为准。`NOTICE` 里列了 ffmpeg 的调用方式、`lib/beat.py` 的来源与重授权状态，以及素材不入库的原因。发布衍生作品前请自行确认第三方素材的授权。
