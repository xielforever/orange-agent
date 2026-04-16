# 移除本地 vCenter Tools（直连能力下线）设计稿

## 背景与目标

当前仓库内置了 `tools/vcenter/*`（pyVmomi 直连 vCenter）并通过工具发现流程注册到 Agent 可调用工具中。由于需要将 vCenter 的所有连接与高危变更审批完全收敛到后端 vCenter MCP，以避免模型通过“换实现路径”绕过审批，本次变更将彻底移除本地 vCenter tools 及其相关配置、测试与文档。

目标：
- Hermes 本地运行时不再加载、注册、暴露任何 vCenter 工具（包含只读与变更类）。
- 仓库内不再保留 vCenter 直连代码与测试，避免误用与供应链/依赖面扩张。
- 清理文档与脚本中对 vCenter tools 的引用，避免误导。

非目标：
- 不在本次变更中新增/替换为 vCenter MCP 客户端实现（后续由外部 MCP 提供并在配置中启用）。
- 不改动审批系统设计（OTP/飞书接入等），仅移除本地 vCenter tools。

## 范围

### 删除内容
- 删除目录：
  - `tools/vcenter/`（包含 `client.py`, `readonly.py`, `mutating.py`, `README.md`, `__init__.py`）
  - `tests/tools/vcenter/`
- 删除/调整脚本：
  - 删除或改写仅用于 vCenter tools 的 patch/debug 脚本（例如 `scripts/patch_readonly.py`、`scripts/patch_approval.py` 如确认与 vCenter tools 强耦合）。
- 清理文档：
  - `docs/` 下与 vCenter tools 集成相关的计划/设计文档与说明（若仅用于 vCenter tools，则删除；若包含通用内容则移除 vCenter 段落）。

### 代码修改点
- 工具发现：从 `model_tools.py::_discover_tools()` 的模块列表中移除：
  - `tools.vcenter.readonly`
  - `tools.vcenter.mutating`
- 工具集定义：从 `toolsets.py` 的 `TOOLSETS` 中移除 `vcenter` toolset 定义（避免配置层继续暴露）。
- CLI 工具配置：从 `hermes_cli/tools_config.py` 中移除 vCenter toolset 的配置入口（以及 VCENTER_* 环境变量引导）。

## 行为变化

变更后：
- `get_available_toolsets()`/工具配置 UI 不再出现 `vcenter`。
- LLM 侧不会再收到任何 `vcenter_*` 的 tool schema，因此无法直接调用本地 vCenter。
- 本地安装环境不再需要 `pyVmomi`（如果仅由 vCenter tools 引入）。

## 兼容性与风险

- 若用户现有 `~/.hermes/config.yaml` 中启用了 `vcenter` toolset，变更后该 toolset 将不可用。
  - 预期行为：工具集校验应提示无效 toolset 或忽略（以现有实现为准）。
- 若第三方代码/脚本直接 import `tools.vcenter.*` 会失败；这是预期破坏性变更，符合“彻底移除”目标。

## 验收标准

- 运行时：
  - 工具发现阶段不再 import vCenter 模块。
  - 工具注册表中不存在任何 `vcenter_*` 工具。
  - `toolsets.py` 与 `hermes tools` 配置 UI 不再出现 vcenter。
- 代码层：
  - 仓库内不存在 `tools/vcenter/` 与 `tests/tools/vcenter/`。
  - `docs/` 与 `scripts/` 不再包含对 vCenter tools 的误导性引用（保留历史发布说明可选，需明确不再支持）。
- 测试：
  - `pytest -m 'not integration'` 通过（移除 vCenter 测试后应无失败）。

## 回滚方案

如需回滚：
- 通过版本控制恢复 `tools/vcenter/`、对应测试与 `model_tools.py/toolsets.py/tools_config.py` 的引用即可。

