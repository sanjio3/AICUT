# 贡献指南

AICUT 以 Skill 目录形式分发，仓库根就是 Skill 根。贡献之前先理解一条边界：宿主 Agent 是运行时，仓库里没有服务、端口、前后端或常驻进程，任何新增能力都不应引入第二个执行入口。

## 本地起环境

需要 Python 3.9 以上与一个可用的 ffmpeg 可执行文件。依赖用 `pip install -r requirements.txt` 安装，代码只用到 numpy、opencv-python 与 PyYAML。

把 `.env.example` 复制成 `.env` 并填入本机路径即可，`ff.load_config` 会自动读取它，`.env` 已被 `.gitignore` 排除。也可以直接导出同名环境变量，优先级是已存在的进程环境变量高于 `.env`，因此 CI 里不会被本机配置覆盖。

手上没有任何素材时，先跑 `python examples/make_demo_assets.py` 生成三段不受版权限制的合成测试视频；不提供 BGM 也可以，`music.load` 会退到等距网格。跑通链路的最短命令是 `python aicut.py prepare` 生成素材索引与卡点数据，接着 `python aicut.py plan --run demo --effects fire-transition,base --duration 6`，再依次 `render` 与 `qa`。任何改动都应至少让这四步无报错，并用 `python aicut.py diff --a <id1> --b <id2>` 确认参数变化能被回传。

## 分工边界

负责人维护 `lib/`、`aicut.py`、根 `SKILL.md`、`params.yaml`、`tests/`、`examples/`、`.github/`、`NOTICE` 与 `pyproject.toml`。同学只在自己认领的 `effects/<name>/` 目录里工作。根 `SKILL.md` 不再有手写路由表，触发词写在各自 frontmatter 的 `triggers` 字段，由 `lib/catalog.py` 自动汇总，因此多人并行不会在同一张共享文件上冲突。`.github/CODEOWNERS` 把这条边界固化成 review 规则。

特效任务分两档，由负责人在 issue 里判定，同学不要自己挑。A 档是参数档，只改 `params.yaml`、准备素材、写 SKILL.md，`run.py` 沿用脚手架的默认实现；B 档是滤镜档，需要写 `filter_complex`，改动 `run.py`。刚上手的人先做 A 档。

## 分支与提交

`main` 只接受 PR，任何人不在 `main` 上直接提交。负责人应在仓库 Settings → Branches 给 `main` 开启保护：Require a pull request before merging，并勾选 Require approvals 1。

分支命名带类型前缀和一个短描述，例如 `feat/fire-transition`、`fix/manga-split-cell`、`docs/readme-demo`。提交信息用 `type(scope): 说明`，type 取 `feat` / `fix` / `docs` / `refactor` / `chore`，scope 写特效名或模块名，说明用中文，一句话讲清改了什么。

一次完整提交的动作序列是这样，逐条执行，不要跳步：

```
git switch main
git pull
git switch -c feat/your-effect
git status
git diff
git add effects/your-effect
git commit -m "feat(your-effect): 一句话说明改了什么"
git push -u origin feat/your-effect
```

推送完成后到仓库页面点 Compare & pull request 开 PR，描述按 `.github/PULL_REQUEST_TEMPLATE.md` 填。合并之后回到本地收尾：

```
git switch main
git pull
git branch -d feat/your-effect
```

`git pull` 报冲突时不要硬合：先 `git rebase --abort` 退回干净状态，再找负责人。冲突处理不是新人的必修项，卡住就停手。

## 新人五步

- 领取 `.github/ISSUE_TEMPLATE/new-effect.md` 任务卡，确认档位、触发词、素材许可与验收指标。
- 执行 `python aicut.py new-effect <name>` 生成三件套，把占位内容换成实际内容。
- 填 `triggers`、`params.yaml` 与 SKILL.md 四段。四段分别是「渲染前必须回传的参数表」「验收」「已知坑」「当前实现边界」，缺一段自检就会拦下。
- 执行 `python aicut.py validate-effect <name>`，再执行 `python aicut.py catalog` 确认能被检索且无 CONFLICTS，最后跑 `python tests/smoke.py`。
- 跑一次 `plan / render / qa`，把实测指标写回 SKILL.md 的「验收」段，附一张效果抽帧图后提 PR。

`run.py` 必须导出纯函数 `build(shot, params, caps) -> (extra_inputs, filter_chain_lines)`，不落盘、不启进程、不读全局配置；基础链输出标签是 `[g]`，额外输入编号从 1 开始，最后一行必须输出 `[out]`。路径与画布尺寸由渲染层注入 `params["_overlays"]`、`params["_assets"]`、`params["_geom"]`，不要自己拼绝对路径。`validate-effect` 会用假 shot 真调一次 `build()`，签名、返回值和 `[out]` 标签写错都能当场发现。

`params.yaml` 里每个可调键都要写 `default`；有 `min/max` 就必须有 `step`，`affects` 指向 `qa.py` 真实输出的指标名，`note` 里写清副作用，因为「改 A 会恶化 B」的耦合比参数本身更值钱。锁定的键用 `locked: true`。

`fire-transition` 是标准范本，参数、素材自动发现、已知坑与实现边界都完整，照它学结构。`manga-split` 与 `ending-dissolve` 目前是简化实现，各自 SKILL.md 的「当前实现边界」里写明了哪些参数尚未真正生效，不要把它们当作完整范例照抄。

不要修改 `lib/` 来适配单个特效。发现某个 ffmpeg 能力缺失时另开 issue，由负责人记进 `lib/doctor.py` 的能力矩阵，让所有 effect 共享。

## 提交之前

- 用 `git status --porcelain` 确认没有成片、素材、`.env`、`__pycache__` 被列入待提交。
- 用 `python tests/smoke.py` 跑零依赖基线，再用 `python aicut.py validate-effect --all` 确认全部特效契约完好。
- 用 `python -m compileall -q .` 确认无语法错误。
- 确认新增代码里没有本机绝对路径、用户名或私有目录名。
- 改了 effect 的 `run.py` 后不必手动清缓存，`shot_key` 已把 `run.py` 内容哈希纳入缓存键。
- 若引入了新的第三方依赖，同步更新 `requirements.txt`、`pyproject.toml` 与 `NOTICE`。

## 关于 1:1 复现

完整视觉内核（文字烘焙、不规则斜切蒙版、拟声字、96 帧交叉溶解序列、定格电光）尚未从 v30 迁移。在此之前的成片是节奏与特效链路正确的样片，不是 v30 的像素级复刻。提交新的视觉能力时，请在对应 effect 的「当前实现边界」段里写清哪些参数尚未真正生效，避免用户误判。
