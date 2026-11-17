## 这次改了什么

一句话说明效果变化，并附上对应的 issue 编号。

## 提交前自检

- [ ] `python aicut.py validate-effect <name>` 全部 PASS
- [ ] `python aicut.py catalog` 无 CONFLICTS，新特效可被检索到
- [ ] `python aicut.py install --dry-run` 能看到它
- [ ] `python tests/smoke.py` 通过
- [ ] `python -m compileall -q .` 无语法错误
- [ ] 只改了 `skills/<name>/`；若改了 `lib/`、`SKILL.md` 或 `params.yaml`，在下面说明原因并 @负责人
- [ ] SKILL.md 四段（渲染前回传参数表 / 验收 / 已知坑 / 当前实现边界）齐全，实测指标已填进「验收」
- [ ] `references/params.yaml` 每个键都有 `default`，有 `min/max` 就有 `step`，`note` 写了副作用
- [ ] `references/pitfalls.md` 已填，没留 TODO
- [ ] SKILL.md frontmatter 有 `name` / `description` / `version` / `agent_created: true`
- [ ] 没有提交素材、成片、`.env`、`__pycache__` 或 `runs/` 下的产物
- [ ] 若引入新依赖或第三方代码，同步更新了 `requirements.txt`、`pyproject.toml`、`NOTICE`

## 实测

把 `qa.json` 的关键数字贴在这里（至少 V、dark_pct、dup_pct、cut_rate），并说明和改动前比是变好还是变差。gate 报 WARN 不要藏着，写清楚原因。

- 效果抽帧图（贴文件或路径）：
- 已知还没做到的部分：
