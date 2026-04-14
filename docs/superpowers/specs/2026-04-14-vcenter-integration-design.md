# 设计规范 (Design Spec): Hermes Agent vCenter AIOps 助手

## 1. 概述
本文档详细说明了如何扩展 Hermes Agent，使其具备原生管理 VMware vCenter 的能力。本助手从一线虚拟化运维工程师的实战视角出发，提供从**全局宏观巡检**到**微观深度诊断**，再到**安全合规变更**的完整自动化工作流。

## 2. 架构与技术路线
采用 **方案一：使用 `pyVmomi` 开发原生 Python 工具**。

- **核心依赖**: `pyVmomi` (VMware 官方 Python SDK)。
- **工具设计原则**: **原子化、高内聚**。摒弃宽泛的“大工具”，将操作拆解为职责单一的小工具（如拆分快照查询、创建、删除为独立工具），以降低大模型调用参数的复杂度并防范幻觉。
- **安全与扩展机制**: 
  - **只读工具**：直接执行。
  - **变更工具**：强制挂载 `@requires_approval` 装饰器进行人工拦截审批。
  - **动态预留**: 工具集将通过动态导入模块的方式设计，方便后期随时向 `tools/vcenter_tools.py` 追加新功能而无需重构核心类。

## 3. vCenter 权限需求 (RBAC)
为保证安全和实现既定功能，分配给 Agent 的 vCenter 服务账号 (`VCENTER_USER`) 必须具备以下最小权限集（建议创建一个自定义 Role 并赋予以下权限）：

- **System**: View, Read (基础全局只读)
- **Virtual Machine**:
  - *Interaction*: Power On, Power Off, Reset, Guest OS Shutdown
  - *Configuration*: Add existing disk, Add new disk, Add/Remove device, Modify device settings (用于热扩容CPU/Mem和调整网卡)
  - *Snapshot management*: Create snapshot, Remove snapshot
  - *Provisioning*: Clone virtual machine (预留扩展用)
- **Host**:
  - *Local operations*: Reconfigure virtual machine
  - *Inventory*: View
- **Datastore**:
  - *Browse datastore* (用于分析孤儿快照文件)
- **Global**:
  - *Diagnostics*, *Health*

## 4. 组件设计与工具矩阵

### 4.1 核心连接包装器 (`tools/vcenter_client.py`)
- 提供 `get_vcenter_connection()` 实现会话保持和 SSL 上下文管理。
- 环境变量依赖：`VCENTER_HOST`, `VCENTER_USER`, `VCENTER_PASSWORD`, `VCENTER_NO_SSL_VERIFY`。

### 4.2 工具集定义 (`tools/vcenter_tools.py`)

#### 维度一：全局巡检类 (免审批)
1. **`vcenter_get_cluster_overview`**: 查询集群 CPU/内存总量及使用率，并拉取 Triggered Alarms。
2. **`vcenter_get_datastore_capacity`**: 扫描存储池，返回总容量及剩余百分比，预警空间不足。
3. **`vcenter_get_recent_critical_events`**: 抓取全局 Error/Warning 级别事件。

#### 维度二：深度排障类 (免审批)
4. **`vcenter_get_vm_performance`**: 查询指定 VM 的 `CPU Ready %`, `Memory Swap/Ballooning` 等深度性能指标。
5. **`vcenter_get_vm_network_info`**: 查询 VM 的 vNIC 状态、绑定的 PortGroup 和 VLAN 信息。
6. **`vcenter_get_vm_snapshots`**: 列出单台 VM 的快照树结构及创建时间。
7. **`vcenter_find_orphan_snapshots`**: 全局扫描存在超过 N 天（如 7 天）的大型快照。
8. **`vcenter_get_host_metrics`**: 查询特定 ESXi 主机的实时负载及硬件传感器健康状态。

#### 维度三：安全变更类 (必须审批)
9. **`vcenter_power_on_vm`**: 将 VM 开机。
10. **`vcenter_power_off_vm`**: 将 VM 强制关机。
11. **`vcenter_create_vm_snapshot`**: 创建新快照。
12. **`vcenter_remove_vm_snapshot`**: 删除指定的单一快照。
13. **`vcenter_hot_add_vm_cpu`**: 热添加 CPU 核数（需 VM 和 OS 支持）。
14. **`vcenter_hot_add_vm_memory`**: 热添加内存（需 VM 和 OS 支持）。
15. **`vcenter_connect_vm_nic`**: 更改虚拟网卡的 Connected 状态。

*(预留插槽：`vcenter_relocate_vm` (vMotion)、`vcenter_clone_vm` 等工具可在后续按需通过相同模式追加)*

## 5. 错误处理与容错
- **参数校验**: 原子化工具必须严格校验参数类型，如遇到重名 VM，强制要求传入附加标识（如 UUID 或 Datacenter 名称）。
- **审批被拒**: 拦截器被用户拒绝时，返回明确的 `{"status": "cancelled"}` 告知模型操作已终止。