# vCenter AIOps 助手实现计划 (Implementation Plan)

> **致 Agent 工作流：** 推荐使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 技能来按任务逐个执行本计划。步骤使用复选框 (`- [ ]`) 语法进行追踪。

**目标:** 扩展 Hermes Agent，使其具备原生的 VMware vCenter 管理能力（包含只读巡检、日志分析以及带审批流的状态变更操作），底层依赖 `pyVmomi`。

**架构:** 创建一个健壮的 vCenter 客户端包装器，实现 5 个具体的工具函数（3 个只读，2 个变更），在 `model_tools.py` 中注册它们的 Schema，并将变更工具与 Hermes 原生的 `_approval_notify_sync`（危险操作审批）机制对接。

**技术栈:** Python 3.11+, `pyvmomi>=8.0.0`, Hermes Agent Tooling Architecture。

---

### 任务 1: 添加依赖与配置说明

**涉及文件:**
- 修改: `requirements.txt`
- 新建: `docs/vcenter_setup.md` (配置说明)

- [ ] **步骤 1: 更新 requirements.txt**

在 `requirements.txt` 的末尾追加 `pyvmomi>=8.0.0`。

```text
pyvmomi>=8.0.0
```

- [ ] **步骤 2: 编写环境变量说明文档**

创建 `docs/vcenter_setup.md` 文件，向用户说明所需的环境变量。

```markdown
# vCenter 配置说明

要启用 vCenter AIOps 工具集，请在环境中设置以下变量：

```bash
export VCENTER_HOST="vcenter.example.com"
export VCENTER_USER="administrator@vsphere.local"
export VCENTER_PASSWORD="your_password"
export VCENTER_NO_SSL_VERIFY="true" # 可选项，设为 true 可忽略自签名证书告警
```
```

- [ ] **步骤 3: 提交代码**

```bash
git add requirements.txt docs/vcenter_setup.md
git commit -m "feat(vcenter): add pyvmomi dependency and configuration docs"
```

---

### 任务 2: 实现核心连接包装器 (Connection Wrapper)

**涉及文件:**
- 新建: `tools/vcenter_client.py`

- [ ] **步骤 1: 编写 vcenter client wrapper**

创建 `tools/vcenter_client.py`，用于处理连接生命周期和基础的搜索工具。

```python
import os
import ssl
import json
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

_vcenter_instance = None

def get_vcenter_connection():
    global _vcenter_instance
    if _vcenter_instance:
        try:
            # 简单检查会话是否仍然存活
            _vcenter_instance.CurrentTime()
            return _vcenter_instance
        except Exception:
            _vcenter_instance = None

    host = os.getenv("VCENTER_HOST")
    user = os.getenv("VCENTER_USER")
    password = os.getenv("VCENTER_PASSWORD")
    
    if not all([host, user, password]):
        raise ValueError("缺少必要的环境变量: VCENTER_HOST, VCENTER_USER, VCENTER_PASSWORD")

    context = None
    if os.getenv("VCENTER_NO_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
        context = ssl._create_unverified_context()

    try:
        si = SmartConnect(host=host, user=user, pwd=password, sslContext=context)
        _vcenter_instance = si
        return si
    except Exception as e:
        raise ConnectionError(f"连接 vCenter {host} 失败: {e}")

def get_obj(content, vimtype, name):
    """
    按名称返回对象。如果 name 为空，则返回找到的第一个对象。
    """
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if name:
            if c.name == name:
                obj = c
                break
        else:
            obj = c
            break
    return obj
```

- [ ] **步骤 2: 提交代码**

```bash
git add tools/vcenter_client.py
git commit -m "feat(vcenter): implement core connection wrapper"
```

---

### 任务 3: 实现只读工具 (巡检与日志分析)

**涉及文件:**
- 新建: `tools/vcenter_tools.py`

- [ ] **步骤 1: 实现巡检与日志工具**

创建 `tools/vcenter_tools.py` 并实现 3 个只读工具。

```python
import json
from datetime import datetime
from .vcenter_client import get_vcenter_connection, get_obj
from pyVmomi import vim

def _safe_json(data):
    try:
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

def vcenter_get_vm_status(vm_name: str) -> str:
    """获取特定虚拟机的 CPU、内存、电源状态和 IP 地址。"""
    try:
        si = get_vcenter_connection()
        vm = get_obj(si.RetrieveContent(), [vim.VirtualMachine], vm_name)
        if not vm:
            return _safe_json({"error": f"未找到名为 '{vm_name}' 的虚拟机。"})
        
        summary = vm.summary
        data = {
            "name": summary.config.name,
            "power_state": summary.runtime.powerState,
            "num_cpu": summary.config.numCpu,
            "memory_mb": summary.config.memorySizeMB,
            "ip_address": summary.guest.ipAddress if summary.guest else None,
            "guest_os": summary.config.guestFullName,
            "overall_status": summary.overallStatus
        }
        return _safe_json(data)
    except Exception as e:
        return _safe_json({"error": str(e)})

def vcenter_get_cluster_health(cluster_name: str = None) -> str:
    """汇总集群内 ESXi 主机的资源和状态。"""
    try:
        si = get_vcenter_connection()
        cluster = get_obj(si.RetrieveContent(), [vim.ClusterComputeResource], cluster_name)
        if not cluster and cluster_name:
             return _safe_json({"error": f"未找到名为 '{cluster_name}' 的集群。"})
        elif not cluster:
            # 如果未指定集群且只有一个集群，回退到全局主机视图
            hosts = si.RetrieveContent().viewManager.CreateContainerView(si.RetrieveContent().rootFolder, [vim.HostSystem], True).view
        else:
            hosts = cluster.host

        host_data = []
        for host in hosts:
            summary = host.summary
            host_data.append({
                "name": host.name,
                "connection_state": summary.runtime.connectionState,
                "power_state": summary.runtime.powerState,
                "cpu_usage_mhz": summary.quickStats.overallCpuUsage,
                "memory_usage_mb": summary.quickStats.overallMemoryUsage,
                "overall_status": summary.overallStatus
            })
        return _safe_json({"hosts": host_data})
    except Exception as e:
        return _safe_json({"error": str(e)})

def vcenter_get_recent_events(vm_name: str, limit: int = 10) -> str:
    """获取虚拟机的最新 vCenter 事件/任务。"""
    try:
        si = get_vcenter_connection()
        content = si.RetrieveContent()
        vm = get_obj(content, [vim.VirtualMachine], vm_name)
        if not vm:
            return _safe_json({"error": f"未找到名为 '{vm_name}' 的虚拟机。"})

        event_manager = content.eventManager
        filter_spec = vim.event.EventFilterSpec()
        entity_spec = vim.event.EventFilterSpec.ByEntity(entity=vm, recursion="self")
        filter_spec.entity = entity_spec
        
        collector = event_manager.CreateCollectorForEvents(filter_spec)
        events = collector.ReadNextEvents(limit)
        collector.DestroyCollector()

        event_data = []
        for event in events:
            event_data.append({
                "event_id": event.key,
                "created_time": event.createdTime.isoformat() if hasattr(event.createdTime, 'isoformat') else str(event.createdTime),
                "user": event.userName,
                "full_message": event.fullFormattedMessage
            })
        return _safe_json({"events": event_data})
    except Exception as e:
        return _safe_json({"error": str(e)})
```

- [ ] **步骤 2: 提交代码**

```bash
git add tools/vcenter_tools.py
git commit -m "feat(vcenter): implement read-only inspection and log tools"
```

---

### 任务 4: 实现变更类工具 (电源管理与快照)

**涉及文件:**
- 修改: `tools/vcenter_tools.py`
- 依赖确认: `tools/approval.py` (确保可以使用 `@requires_approval` 装饰器)

- [ ] **步骤 1: 在 `tools/vcenter_tools.py` 中追加变更类工具**

在文件顶部引入拦截装饰器，并追加代码：

```python
# 在 tools/vcenter_tools.py 顶部添加导入
from tools.approval import requires_approval
import time

# 追加以下函数

def _wait_for_task(task):
    """等待 vSphere 任务完成并返回状态"""
    task_done = False
    while not task_done:
        if task.info.state == 'success':
            return True, task.info.result
        if task.info.state == 'error':
            return False, task.info.error.msg
        time.sleep(1)

@requires_approval(description="虚拟机电源管理操作（开机、关机、重启）")
def vcenter_power_manage_vm(vm_name: str, action: str) -> str:
    """开启、关闭或重启虚拟机。"""
    valid_actions = ['power_on', 'power_off', 'reboot_guest', 'reset']
    if action not in valid_actions:
        return _safe_json({"error": f"无效的操作，必须是 {valid_actions} 之一"})

    try:
        si = get_vcenter_connection()
        vm = get_obj(si.RetrieveContent(), [vim.VirtualMachine], vm_name)
        if not vm:
            return _safe_json({"error": f"未找到名为 '{vm_name}' 的虚拟机。"})

        task = None
        if action == 'power_on':
            task = vm.PowerOn()
        elif action == 'power_off':
            task = vm.PowerOff()
        elif action == 'reboot_guest':
            vm.RebootGuest() # RebootGuest 不返回 standard task
            return _safe_json({"status": "success", "message": f"已向 {vm_name} 发送重启 Guest OS 指令"})
        elif action == 'reset':
            task = vm.Reset()

        if task:
            success, result = _wait_for_task(task)
            if success:
                return _safe_json({"status": "success", "message": f"操作 '{action}' 在 {vm_name} 上执行成功"})
            else:
                return _safe_json({"error": f"操作 '{action}' 执行失败: {result}"})
        
        return _safe_json({"error": "无法初始化任务"})
    except Exception as e:
        return _safe_json({"error": str(e)})

@requires_approval(description="为虚拟机创建快照")
def vcenter_create_snapshot(vm_name: str, snapshot_name: str, description: str = "") -> str:
    """在进行高危操作前为虚拟机创建快照。"""
    try:
        si = get_vcenter_connection()
        vm = get_obj(si.RetrieveContent(), [vim.VirtualMachine], vm_name)
        if not vm:
            return _safe_json({"error": f"未找到名为 '{vm_name}' 的虚拟机。"})

        memory = False
        quiesce = False
        task = vm.CreateSnapshot(snapshot_name, description, memory, quiesce)
        
        success, result = _wait_for_task(task)
        if success:
            return _safe_json({"status": "success", "message": f"已成功为 {vm_name} 创建快照 '{snapshot_name}'"})
        else:
            return _safe_json({"error": f"快照创建失败: {result}"})
    except Exception as e:
        return _safe_json({"error": str(e)})
```

- [ ] **步骤 2: 提交代码**

```bash
git add tools/vcenter_tools.py
git commit -m "feat(vcenter): implement mutating tools with approval gating"
```

---

### 任务 5: 在 `model_tools.py` 中注册工具

**涉及文件:**
- 修改: `model_tools.py`

- [ ] **步骤 1: 导入新工具**

在 `model_tools.py` 顶部导入新编写的函数：
```python
from tools.vcenter_tools import (
    vcenter_get_vm_status,
    vcenter_get_cluster_health,
    vcenter_get_recent_events,
    vcenter_power_manage_vm,
    vcenter_create_snapshot
)
```

- [ ] **步骤 2: 在 `get_tool_definitions` 中添加 JSON Schema**

在 `get_tool_definitions()` 函数内部，增加对 `vcenter` 工具集的支持：

```python
    # ... inside get_tool_definitions ...
    if "vcenter" in toolsets:
        tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "vcenter_get_vm_status",
                    "description": "获取特定 VMware 虚拟机的 CPU、内存、电源状态和 IP 地址。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vm_name": {"type": "string", "description": "虚拟机的确切名称"}
                        },
                        "required": ["vm_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "vcenter_get_cluster_health",
                    "description": "汇总 VMware 集群内 ESXi 主机的资源和状态。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cluster_name": {"type": "string", "description": "集群名称（可选，留空则查询所有主机）"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "vcenter_get_recent_events",
                    "description": "获取虚拟机的最新 vCenter 事件/任务记录，用于诊断问题。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vm_name": {"type": "string", "description": "虚拟机的确切名称"},
                            "limit": {"type": "integer", "description": "要检索的事件数量（默认 10）"}
                        },
                        "required": ["vm_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "vcenter_power_manage_vm",
                    "description": "开启、关闭、重启或重置虚拟机。此操作需要用户审批。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vm_name": {"type": "string", "description": "虚拟机的确切名称"},
                            "action": {
                                "type": "string", 
                                "enum": ["power_on", "power_off", "reboot_guest", "reset"],
                                "description": "要执行的电源操作"
                            }
                        },
                        "required": ["vm_name", "action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "vcenter_create_snapshot",
                    "description": "在进行高危操作前为虚拟机创建快照。此操作需要用户审批。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vm_name": {"type": "string", "description": "虚拟机的确切名称"},
                            "snapshot_name": {"type": "string", "description": "简短且具有描述性的快照名称"},
                            "description": {"type": "string", "description": "详细描述创建该快照的原因"}
                        },
                        "required": ["vm_name", "snapshot_name", "description"]
                    }
                }
            }
        ])
```

- [ ] **步骤 3: 在 `handle_function_call` 中映射路由**

在 `handle_function_call()` 内部，添加路由分发逻辑：

```python
    # ... inside handle_function_call ...
    elif function_name == "vcenter_get_vm_status":
        return vcenter_get_vm_status(args.get("vm_name"))
    elif function_name == "vcenter_get_cluster_health":
        return vcenter_get_cluster_health(args.get("cluster_name"))
    elif function_name == "vcenter_get_recent_events":
        return vcenter_get_recent_events(args.get("vm_name"), args.get("limit", 10))
    elif function_name == "vcenter_power_manage_vm":
        return vcenter_power_manage_vm(args.get("vm_name"), args.get("action"))
    elif function_name == "vcenter_create_snapshot":
        return vcenter_create_snapshot(args.get("vm_name"), args.get("snapshot_name"), args.get("description", ""))
```

- [ ] **步骤 4: 提交代码**

```bash
git add model_tools.py
git commit -m "feat(vcenter): register vcenter tools in model_tools.py"
```