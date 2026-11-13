---
name: 新增 / 认领一个特效
about: 收集并封装一个新的剪辑特效，交付 effects/<name>/ 三件套
title: "[effect] <特效名>"
labels: effect
assignees: ''
---

## 任务分档

先由负责人判定档位，不要自己挑。

- **A 档（参数档）**：只改 `params.yaml`、准备素材、写 SKILL.md，`run.py` 用模板里的默认实现。适合刚上手的同学。
- **B 档（滤镜档）**：需要写 `filter_complex`，改 `run.py`。由负责人确认后再开工。

## 基本信息

- 特效名（小写英文加连字符，例如 `sparkle-cut`）：
- 用户会怎么说它（列 2–5 个触发词，中英文都写）：
- 参考片段出处与时间点（链接 / 文件名 / 秒数）：
- 用在片子的哪个段落（开场 / 主歌 / 副歌 / 结尾 / 全片）：

## 素材

- 需要哪类叠加素材，来源与许可是否已确认：
- 不需要额外素材，只用画面本身（是 / 否）：
- 素材是否已放进本机 `materials/overlays/`（仓库不收素材）：

## 参数草案

先用 `python aicut.py new-effect <name>` 生成三件套，再填下面这几项。

- 打算暴露几个旋钮（建议 3–7 个，其余进 preset）：
- 每个旋钮的默认值、范围、影响的 `qa.json` 指标名：
- 有没有锁定项，为什么锁定：

## 验收

- [ ] `python aicut.py validate-effect <name>` 全部 PASS
- [ ] `python aicut.py catalog` 能看到新特效且无 CONFLICTS
- [ ] `python tests/smoke.py` 通过
- [ ] 跑过一次 `plan / render / qa`，把实测指标写进 SKILL.md 的「验收」段
- [ ] SKILL.md 的「已知坑」与「当前实现边界」如实填写，没有把简化实现说成完整实现
- [ ] 附一张效果截图或抽帧图

## 边界

只改 `effects/<name>/` 里的文件。不要改 `lib/`、`SKILL.md`、`params.yaml`、`pyproject.toml` 或别人的 effect 目录；确实需要改内核时，另开一个 issue 交负责人处理。

认领人：
