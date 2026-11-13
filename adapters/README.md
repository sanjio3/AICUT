# MCP 薄适配（可选，默认不启用）

AICUT 的主形态是 Skill。Skill 靠触发词与渐进披露工作，零进程、零端口、零依赖，正好匹配「用户说火焰转场就调用」的场景。这里保留一个单文件位置，供确有外部 Agent 或 IDE 需要集成时使用。

需要接入时，新增一个 `mcp.mjs`，用 `@modelcontextprotocol/sdk` 起 stdio server，把 `lib/` 的函数注册成 tools 即可，不新建架构层、不复制任何业务逻辑。建议的 tools 与 `aicut.py` 的五个动作一一对应：

- `doctor` → `lib.doctor.probe()`
- `params` → `lib.plan.param_table()`
- `plan` / `render` / `qa` / `diff` → 同名 lib 函数

输入输出全部是 JSON 契约，不返回大段日志；progress 与 logging 用来把逐镜状态推给调用方前端。该依赖只属于 adapter，不应写进核心 `requirements.txt`，否则会把零依赖插件变成需要 Node 运行时的工程。

在没有明确外部集成需求之前，这个文件保持为空目录。
