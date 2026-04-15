# 设计规范 (Design Spec): Hermes Agent vCenter AIOps 助手 (满配版)

## 1. 概述
本文档详细说明了如何扩展 Hermes Agent，使其具备原生管理 VMware vCenter 的能力。本助手从一线虚拟化运维工程师的实战视角出发，提供从**全局宏观巡检**到**微观深度诊断**，再到**安全合规变更**的完整自动化工作流。本次设计包含了多达 **33 个高度原子化的工具**，覆盖了计算、存储、网络和高可用调度的绝大多数日常场景。

## 2. 架构与技术路线
采用 **方案一：使用 `pyVmomi` 开发原生 Python 工具**。

- **核心依赖**: `pyVmomi` (VMware 官方 Python SDK)。
- **工具设计原则**: **原子化、高内聚**。将操作拆解为职责单一的小工具（例如：不仅拆分了快照的查、建、删，连虚拟机关机都细分为强制断电和优雅关机），以降低大模型调用参数的复杂度，防范幻觉。
- **安全与扩展机制**: 
  - **只读工具**：直接执行。
  - **变更工具**：强制挂载 `@requires_approval` 装饰器进行人工拦截审批。
  - **动态预留**: 采用 `importlib` 动态加载，后续新增工具无需修改框架核心代码。

## 3. vCenter 权限需求 (RBAC)
分配给 Agent 的账号需具备以下自定义权限（最小权限集）：
- **System**: View, Read
- **Virtual Machine**:
  - *Interaction*: Power On, Power Off, Reset, Guest OS Shutdown, Console Interaction (截图用)
  - *Configuration*: Add existing disk, Add new disk, Add/Remove device, Modify device settings
  - *Snapshot management*: Create snapshot, Remove snapshot
  - *Provisioning*: Clone virtual machine
- **Host**:
  - *Local operations*: Reconfigure virtual machine
  - *Inventory*: View
  - *Configuration*: Network configuration, Maintenance
- **Datastore**:
  - *Browse datastore* (用于分析孤儿文件)
- **Global**:
  - *Diagnostics*, *Health*

## 4. 工具矩阵 (共 33 个原子化工具)

### 4.1 维度一：全局巡检类 (A类 - 免审批)
*用于日常早检和全局状态速览。*
1. **`vcenter_get_cluster_overview`**: 查询集群 CPU/内存总量及使用率，拉取 Triggered Alarms。
2. **`vcenter_get_datastore_capacity`**: 扫描存储池，返回总容量及剩余百分比。
3. **`vcenter_get_recent_critical_events`**: 抓取全局 Error/Warning 级别事件。
4. **`vcenter_get_top_cpu_vms`**: 全局扫描，返回当前 CPU 消耗最高的 Top N 台虚拟机。
5. **`vcenter_get_top_memory_vms`**: 全局扫描，返回当前内存活跃最高的 Top N 台虚拟机。
6. **`vcenter_get_powered_off_vms`**: 扫描并返回当前处于关机状态的 VM 列表。
7. **`vcenter_get_vm_events_timeline`**: 拉取指定 VM 在最近 N 小时内的完整事件流水。

### 4.2 维度二：深度排障类 (A类 - 免审批)
*用于定位单机或局部的疑难杂症。*
8. **`vcenter_get_vm_config`**: 查询 VM 基础配置（IP、Guest OS、挂载的 ISO）。
9. **`vcenter_get_vm_performance`**: 查询 VM 深度性能（CPU Ready, Swap, Ballooning）。
10. **`vcenter_get_vm_disk_usage`**: 查询 VM 的每个虚拟磁盘的真实大小及所在 Datastore 路径。
11. **`vcenter_get_vm_network_info`**: 查询 VM 的 vNIC 连接状态及绑定的 PortGroup/VLAN。
12. **`vcenter_get_host_metrics`**: 查询特定 ESXi 主机的实时负载及硬件传感器状态。
13. **`vcenter_get_host_network_topology`**: 查询宿主机 vSwitch、物理网卡 (vmnic) 链路状态及 CDP/LLDP。
14. **`vcenter_get_vm_snapshots`**: 列出单台 VM 的快照树。
15. **`vcenter_find_orphan_snapshots`**: 扫描存在超过 N 天的大型快照。
16. **`vcenter_get_drs_recommendations`**: 拉取集群当前的 DRS 迁移建议及反亲和性规则。
17. **`vcenter_get_vm_console_screenshot`**: 截取虚拟机当前 Console 画面（用于排查蓝屏/紫屏）。

### 4.3 维度三：安全变更类 (B类 - 必须审批)
*用于执行具有破坏性或改变系统状态的操作。*
18. **`vcenter_power_on_vm`**: 将 VM 开机。
19. **`vcenter_power_off_vm`**: 强制断电。
20. **`vcenter_shutdown_guest_os`**: 优雅关机 (需要 VMware Tools)。
21. **`vcenter_reset_vm`**: 强制重启。
22. **`vcenter_create_vm_snapshot`**: 创建新快照。
23. **`vcenter_remove_vm_snapshot`**: 删除指定的单一快照。
24. **`vcenter_remove_all_vm_snapshots`**: 清空某台 VM 的所有快照。
25. **`vcenter_hot_add_vm_cpu`**: 热添加 CPU。
26. **`vcenter_hot_add_vm_memory`**: 热添加内存。
27. **`vcenter_expand_vm_disk`**: 扩展特定虚拟磁盘的容量。
28. **`vcenter_connect_vm_nic`**: 重新连接已断开的虚拟网卡。
29. **`vcenter_change_vm_network`**: 将 vNIC 切换到另一个 PortGroup (更改 VLAN)。
30. **`vcenter_restart_guest_network`**: 模拟拔插网线（断开连通后延时 3 秒再连接）。
31. **`vcenter_mount_iso_to_vm`**: 挂载 Datastore 中的 ISO 文件。
32. **`vcenter_enter_maintenance_mode`**: 将主机置于维护模式并触发 VM 疏散。
33. **`vcenter_clone_vm`**: 基础交付，从模板克隆虚拟机。

## 5. 错误处理与容错
- **参数校验**: 原子化工具必须严格校验参数类型，如遇到重名 VM，强制要求传入 UUID。
- **长耗时任务处理**: 对于克隆 (`vcenter_clone_vm`) 或进入维护模式，需返回 Task ID 并支持异步查询，防止 Agent 线程超时。