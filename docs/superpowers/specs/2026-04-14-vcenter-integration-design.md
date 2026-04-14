# 设计规范 (Design Spec): Hermes Agent vCenter AIOps 助手

## 1. 概述
本文档详细说明了如何扩展 Hermes Agent，使其具备原生管理 VMware vCenter 的能力。我们的目标是打造一个“AIOps 助手”，它可以自主执行只读性质的基础设施巡检、日志分析，并在严格的审批流控制下执行高危变更操作（如电源管理、创建快照等）。

## 2. 架构与技术路线
我们将采用 **方案一：使用 `pyVmomi` 开发原生 Python 工具**。
该方案会在 Hermes Agent 现有的 `tools/` 目录下创建一个专属的工具集。

- **核心依赖库**: `pyVmomi` (VMware 官方提供的 vSphere API Python 客户端)。
- **集成方式**: 工具将带有标准的 JSON Schemas，并在 `model_tools.py` 中注册。
- **安全与权限控制**: 
  - **只读工具**：Agent 可以随时直接调用并返回结果。
  - **变更/状态突变工具**：将利用 Hermes 原生的 `@requires_approval` 装饰器或 `_approval_notify_sync` 机制。在执行前，工具会暂停并向 CLI/Gateway 平台的用户推送审批请求。

## 3. 组件设计

### 3.1 依赖项与配置
- **新增依赖**: 在 `requirements.txt` 中添加 `pyvmomi>=8.0.0`。
- **环境变量**:
  - `VCENTER_HOST`: vCenter 服务器的 IP 地址或 FQDN。
  - `VCENTER_USER`: 具有读写权限的服务账号用户名。
  - `VCENTER_PASSWORD`: 服务账号的密码。
  - `VCENTER_NO_SSL_VERIFY`: (可选) 设置为 `true` 可绕过自签名证书的验证错误。

### 3.2 核心连接包装器 (Connection Wrapper)
将创建一个工具模块 (`tools/vcenter_client.py`) 来管理 vCenter 的连接生命周期：
- 提供一个健壮的 `get_vcenter_connection()` 函数。
- 处理 SSL 上下文并维持 Session 存活。
- 提供辅助函数，以便通过名称或 UUID 递归搜索虚拟机 (VM) 对象。

### 3.3 工具定义 (执行动作)
我们将创建一个新文件 `tools/vcenter_tools.py`，包含以下工具函数：

#### 类别 A: 只读 (巡检与日志) - 无需审批
1.  **`vcenter_get_vm_status(vm_name: str) -> dict`**
    - **用途**: 获取特定虚拟机的 CPU、内存、电源状态和 IP 地址。
2.  **`vcenter_get_cluster_health(cluster_name: Optional[str] = None) -> dict`**
    - **用途**: 汇总指定集群（或所有主机）内 ESXi 主机的总资源、使用率和告警状态。
3.  **`vcenter_get_recent_events(vm_name: str, limit: int = 10) -> str`**
    - **用途**: 获取虚拟机的最新 vCenter 事件/任务记录，用于诊断死机或网络中断等问题。

#### 类别 B: 变更 (状态突变) - 必须审批
1.  **`vcenter_power_manage_vm(vm_name: str, action: str) -> str`**
    - **用途**: 开启、关闭或重启虚拟机。
    - **支持的动作**: `power_on`, `power_off`, `reboot_guest`, `reset`。
    - **审批逻辑**: 在调用 `Task.WaitTask` 真正执行前，触发 Hermes 的审批提示。
2.  **`vcenter_create_snapshot(vm_name: str, snapshot_name: str, description: str) -> str`**
    - **用途**: 在进行高危操作前为虚拟机创建快照。
    - **审批逻辑**: 触发 Hermes 的审批提示。

### 3.4 与 Hermes 集成
1.  **工具注册**:
    更新 `model_tools.py`：
    - 在 `get_tool_definitions()` 函数中，新增一个 `"vcenter"` 工具集分类，并添加上述 5 个工具的 JSON Schema 定义。
    - 在 `handle_function_call()` 中，将大模型返回的工具名称映射并分发到对应的 Python 函数。
2.  **审批流接入**:
    确保变更类工具使用了上下文感知的审批流。如果在 Gateway 模式（如 Slack, Discord, Telegram, 飞书等）下执行，系统会自动向用户推送可交互的审批卡片或消息。

## 4. 错误处理与边缘场景
- **连接失败**: 如果无法连通 vCenter，工具必须返回清晰的 JSON 错误信息（例如 `{"error": "..."}`），而不是直接抛出异常导致 Agent 线程崩溃。
- **重名虚拟机**: 如果出现名称冲突，连接包装器应返回错误，提示大模型需要提供更具体的 Datacenter 或 UUID 进行精确定位。
- **审批被拒绝**: 如果用户拒绝了危险操作，工具将返回 `{"status": "cancelled", "reason": "User denied the operation"}`，以便大模型知道操作已终止。

## 5. 安全注意事项
- **凭证隔离**: 账号密码绝不能被打印到日志中，也不能传入大模型的上下文中。它们必须严格保留在系统的环境变量里。
- **最小权限调用**: `pyVmomi` 客户端只允许执行本工具集内显式定义的 API 调用，防止大模型尝试对 vCenter 执行未授权的任意代码。