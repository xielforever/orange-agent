# vCenter AIOps 工具集 (vCenter AIOps Tools)

该目录包含了专为 VMware vCenter 设计的自动化智能运维 (AIOps) 原子工具集。所有工具都遵循“读写分离”的安全架构设计，旨在供 AI Agent 安全、高效地调用，以完成从监控巡检、深度排障到自愈变更的完整运维闭环。

## 目录结构与架构设计

工具集被严格划分为三个核心模块：

*   **`client.py`**: 负责与 vCenter 的基础连接和认证。它封装了 `pyVmomi` 客户端，并提供安全的单例会话管理和基础的对象查询辅助函数。
*   **`readonly.py`**: **A 类只读排障工具集**。包含了所有查询、监控、指标收集等不会对 vCenter 环境产生任何修改状态的工具。
*   **`mutating.py`**: **B 类高危变更工具集**。包含了所有涉及修改 vCenter 状态的操作（如电源管理、快照、资源扩容、网络变更等）。此模块内的所有对外暴露的工具方法均通过 `@requires_approval` 装饰器进行拦截，确保 AI 代理在执行变更前必须获得人类管理员的授权确认。

## 前置环境依赖

1.  **Python 包依赖**：
    *   `pyvmomi` (VMware 官方 SDK)
    *   `requests` / `urllib3` (用于处理潜在的忽略 SSL 证书告警)
    *   运行 `pip install pyvmomi` 即可安装核心依赖。

2.  **环境变量配置**：
    工具在运行时会自动读取以下环境变量来建立与 vCenter 的连接：
    *   `VCENTER_HOST`: vCenter 服务器的 IP 地址或 FQDN (例如: `vcenter.example.com`)
    *   `VCENTER_USER`: 具有适当权限的 vCenter 登录账号 (例如: `administrator@vsphere.local`)
    *   `VCENTER_PASSWORD`: 对应的登录密码
    *   *(可选)* `VCENTER_NO_SSL_VERIFY`: 如果设置为 `1` 或 `true`，将跳过 vCenter 的自签名 SSL 证书校验。

## 工具列表清单

### A 类只读工具 (`readonly.py`) - 共 18 个
这些工具可以直接并安全地并发调用：
*   `vcenter_get_cluster_overview`: 查询集群的 CPU/内存总量、使用率及触发的告警。
*   `vcenter_get_datastore_capacity`: 扫描存储池，返回总容量、剩余容量及剩余百分比。
*   `vcenter_get_recent_critical_events`: 抓取全局的 Error/Warning 级别近期事件。
*   `vcenter_get_top_cpu_vms`: 获取 CPU 消耗 Top N 的虚拟机列表。
*   `vcenter_get_top_memory_vms`: 获取内存活跃 Top N 的虚拟机列表。
*   `vcenter_get_powered_off_vms`: 获取当前处于关机状态的所有虚拟机。
*   `vcenter_get_vm_events_timeline`: 拉取指定虚拟机在最近 N 小时内的完整事件流水。
*   `vcenter_get_vm_config`: 查询虚拟机基础配置（IP、Guest OS 状态等）。
*   `vcenter_get_vm_performance`: 深度查询虚拟机的性能指标（如 CPU Ready、Swap、Ballooning 等）。
*   `vcenter_get_vm_disk_usage`: 查询虚拟机的各个磁盘真实占用情况及所在存储路径。
*   `vcenter_get_vm_network_info`: 查询虚拟机的 vNIC 连接状态及绑定的 PortGroup/VLAN。
*   `vcenter_get_hosts_overview`: 概览指定集群（或全部）ESXi 主机的总资源、使用率和告警状态。
*   `vcenter_get_host_metrics`: 查询特定 ESXi 主机的实时负载及硬件传感器摘要。
*   `vcenter_get_host_network_topology`: 查询 ESXi 宿主机的物理网卡 (vmnic) 及 vSwitch 拓扑。
*   `vcenter_get_vm_snapshots`: 列出单台虚拟机的完整快照树。
*   `vcenter_find_orphan_snapshots`: 扫描并找出存在超过指定天数的大型“孤儿”快照。
*   `vcenter_get_drs_recommendations`: 获取集群当前的 DRS 迁移建议及负载均衡情况。
*   `vcenter_get_vm_console_screenshot`: 获取虚拟机当前控制台画面的截图（通常用于 AI 视觉排查蓝屏/宕机）。

### B 类变更工具 (`mutating.py`) - 共 15 个
**⚠️ 警告：调用以下工具将改变 vCenter 基础设施状态，请确保具备相应权限并在执行前仔细审查参数。**
*   **电源与状态管理**：
    *   `vcenter_power_on_vm`: 将虚拟机开机。
    *   `vcenter_power_off_vm`: 强制将虚拟机关机（断电）。
    *   `vcenter_shutdown_guest_os`: 优雅地关闭虚拟机 Guest OS（需要 VMware Tools 支持）。
    *   `vcenter_reset_vm`: 强制重启虚拟机。
*   **快照管理**：
    *   `vcenter_create_vm_snapshot`: 为虚拟机创建新快照。
    *   `vcenter_remove_vm_snapshot`: 删除指定的单一快照。
    *   `vcenter_remove_all_vm_snapshots`: 清空虚拟机的整个快照树。
*   **资源调整与配置**：
    *   `vcenter_hot_add_vm_cpu`: 热添加虚拟机 CPU 核心数。
    *   `vcenter_hot_add_vm_memory`: 热添加虚拟机内存。
    *   `vcenter_expand_vm_disk`: 扩展特定虚拟磁盘的容量。
    *   `vcenter_mount_iso_to_vm`: 将 Datastore 中的 ISO 文件挂载到虚拟机的光驱。
*   **网络排障与调整**：
    *   `vcenter_connect_vm_nic`: 重新连接已断开的虚拟网卡。
    *   `vcenter_change_vm_network`: 将虚拟网卡切换到另一个网络（PortGroup/VLAN）。
    *   `vcenter_restart_guest_network`: 模拟物理拔插网线（断开网卡连接并延迟后重新连接）。
*   **高级运维操作**：
    *   `vcenter_enter_maintenance_mode`: 将 ESXi 主机置于维护模式，并触发虚拟机疏散。
    *   `vcenter_clone_vm`: 从源虚拟机克隆创建新的虚拟机。

## 测试与开发验证
工具集包含了完整的离线 Mock 测试支持，即使在没有连接真实 vCenter 环境的情况下也可以验证逻辑。
您可以通过以下命令运行完整的单元测试集（位于 `tests/tools/vcenter/` 目录）：
```bash
pytest tests/tools/vcenter/ -v
```
测试框架通过动态替换和拦截 `pyVmomi` 的严格类型校验机制，实现了一个轻量级的内存 vCenter 假实例，保证了 TDD 开发的高效进行。