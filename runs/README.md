# runs/

每次出片一个 `<id>/` 子目录，append-only，不覆盖历史。目录内容由 `aicut.py plan / render / qa` 生成，被 `.gitignore` 排除，只留这份说明。

- `params.yaml` 本次用户 overrides，可直接编辑后重跑 `plan --run <id>`。
- `effective.yaml` 合并后的全量标量参数，用于复现。
- `plan.json` 逐镜决策，含每个镜头的 effect 与参数子集。
- `../_cache/shots/` 跨 run 共享的逐镜片段，文件名即内容哈希，命中即跳过重渲。所有 run 共用，改一个参数只让命中的镜头失效。
- `silent.mp4` / `final.mp4` 无声母版与成片。
- `qa.json` / `gate.json` 指标与 gate 判定。
- `feedback.yaml` 用户原话、归因、改动与是否采纳，供下一轮检索。

`python aicut.py diff --a <id1> --b <id2>` 比较两次的 overrides 与指标，回传「改了哪几个键、指标怎么变」。
