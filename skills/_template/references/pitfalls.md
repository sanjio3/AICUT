# <NAME> 参数与踩坑

这个文件是 SKILL.md 的详细版，给需要深入调参或改实现的 Agent / 开发者读。
SKILL.md 只讲「何时用、怎么用」，细节放这里。

## 参数表

TODO 逐项列出 `references/params.yaml` 里的旋钮：名称、默认值、范围、影响的 qa 指标、
副作用。与 `python aicut.py params --effect <NAME>` 的输出保持一致。

## 验收阈值

TODO 写清这个特效关注的指标与合理区间。参照 `lib/qa.py` 的九项指标命名，
至少覆盖亮度类（V / dark_pct / bright_pct）与清晰度类（laplacian_var / motion_p90）各一项。

## 已知坑

TODO 写这本机 ffmpeg 构建的限制、素材要求、容易踩的坑。全局限制见 `lib/doctor.py`。

## 当前实现边界

TODO 写清哪些参数还没真正生效、哪些视觉效果尚未实现、和参考片差在哪里。
不许留空，不许把简化实现说成完整实现。
