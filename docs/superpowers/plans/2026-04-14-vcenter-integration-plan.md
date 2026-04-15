# vCenter AIOps 助手实现计划 (Implementation Plan)

> **致 Agent 工作流：** 推荐使用 `superpowers:subagent-driven-development` 或 `superpowers:executing-plans` 技能来按任务逐个执行本计划。步骤使用复选框 (`- [ ]`) 语法进行追踪。

**目标:** 扩展 Hermes Agent，提供基于实战场景拆解的 33 个原子化 VMware vCenter 管理工具（包含全局巡检、深度排障及安全变更）。

**技术栈:** Python 3.11+, `pyvmomi>=8.0.0`, Hermes Agent Tooling Architecture。

---

### 任务 1: 添加依赖与权限配置说明

**涉及文件:**
- 修改: `requirements.txt`
- 新建: `docs/vcenter_setup.md`

- [ ] **步骤 1: 更新 requirements.txt**

在 `requirements.txt` 的末尾追加 `pyvmomi>=8.0.0`。

```text
pyvmomi>=8.0.0
```

- [ ] **步骤 2: 编写环境变量与 RBAC 权限说明文档**

创建 `docs/vcenter_setup.md`。

```markdown
# vCenter 配置与权限说明

## 1. 环境变量
请在环境中设置以下变量：
```bash
export VCENTER_HOST="vcenter.example.com"
export VCENTER_USER="administrator@vsphere.local"
export VCENTER_PASSWORD="your_password"
export VCENTER_NO_SSL_VERIFY="true"
```

## 2. 最小权限集 (RBAC)
分配给 Agent 的账号需具备以下自定义权限：
- **System**: View, Read
- **Virtual Machine**:
  - Interaction: Power On, Power Off, Reset, Guest OS Shutdown, Console Interaction
  - Configuration: Add existing disk, Add new disk, Add/Remove device, Modify device settings
  - Snapshot management: Create snapshot, Remove snapshot
  - Provisioning: Clone virtual machine
- **Host**: Local operations -> Reconfigure virtual machine, Inventory -> View
- **Datastore**: Browse datastore
- **Global**: Diagnostics, Health
```

- [ ] **步骤 3: 提交代码**

```bash
git add requirements.txt docs/vcenter_setup.md
git commit -m "feat(vcenter): add dependencies and rbac docs"
```

---

### 任务 2: 实现核心连接包装器

**涉及文件:**
- 新建: `tools/vcenter_client.py`

- [ ] **步骤 1: 编写 vcenter_client.py**

```python
import os
import ssl
from pyVim.connect import SmartConnect
from pyVmomi import vim

_vcenter_instance = None

def get_vcenter_connection():
    global _vcenter_instance
    if _vcenter_instance:
        try:
            _vcenter_instance.CurrentTime()
            return _vcenter_instance
        except Exception:
            _vcenter_instance = None

    host = os.getenv("VCENTER_HOST")
    user = os.getenv("VCENTER_USER")
    pwd = os.getenv("VCENTER_PASSWORD")
    
    if not all([host, user, pwd]):
        raise ValueError("缺少必要的环境变量: VCENTER_HOST, VCENTER_USER, VCENTER_PASSWORD")

    context = ssl._create_unverified_context() if os.getenv("VCENTER_NO_SSL_VERIFY", "").lower() in ("true", "1") else None

    try:
        _vcenter_instance = SmartConnect(host=host, user=user, pwd=pwd, sslContext=context)
        return _vcenter_instance
    except Exception as e:
        raise ConnectionError(f"连接 vCenter {host} 失败: {e}")

def get_obj(content, vimtype, name):
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if name and c.name == name:
            return c
        elif not name:
            return c
    return None
```

- [ ] **步骤 2: 提交代码**

```bash
git add tools/vcenter_client.py
git commit -m "feat(vcenter): core connection wrapper"
```

---

### 任务 3: 实现全局巡检与深度诊断工具 (A类 - 免审批)

**涉及文件:**
- 新建: `tools/vcenter_tools_readonly.py` (按文件拆分避免单个文件过长)

- [ ] **步骤 1: 编写只读巡检工具集**

```python
import json
from pyVmomi import vim
from .vcenter_client import get_vcenter_connection, get_obj

def _safe_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)

# ---- 维度一：全局巡检类 (1-7) ----
def vcenter_get_cluster_overview(cluster_name: str = None) -> str:
    """查询集群 CPU/内存总量及使用率"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_datastore_capacity() -> str:
    """扫描存储池返回容量及剩余百分比"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_recent_critical_events(limit: int = 10) -> str:
    """抓取全局 Error/Warning 事件"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_top_cpu_vms(limit: int = 5) -> str:
    """获取 CPU 消耗 Top N 虚拟机"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_top_memory_vms(limit: int = 5) -> str:
    """获取内存消耗 Top N 虚拟机"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_powered_off_vms() -> str:
    """获取所有关机状态的虚拟机"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_vm_events_timeline(vm_name: str, hours: int = 24) -> str:
    """获取虚拟机近期事件时间线"""
    return _safe_json({"status": "placeholder_for_implementation"})

# ---- 维度二：深度排障类 (8-17) ----
def vcenter_get_vm_config(vm_name: str) -> str:
    """获取虚拟机基础配置信息"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_vm_performance(vm_name: str) -> str:
    """查询 VM 深度性能指标 (Ready, Swap, Balloon)"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_vm_disk_usage(vm_name: str) -> str:
    """查询虚拟机各个磁盘真实占用情况"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_vm_network_info(vm_name: str) -> str:
    """查询 VM 的 vNIC 状态和绑定的 PortGroup"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_host_metrics(host_name: str) -> str:
    """查询特定 ESXi 主机实时负载及硬件传感器"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_host_network_topology(host_name: str) -> str:
    """查询宿主机物理网卡及 vSwitch 拓扑"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_vm_snapshots(vm_name: str) -> str:
    """列出单台 VM 的快照树"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_find_orphan_snapshots(days_old: int = 7) -> str:
    """扫描超期大型快照"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_drs_recommendations(cluster_name: str = None) -> str:
    """获取集群 DRS 建议及冲突规则"""
    return _safe_json({"status": "placeholder_for_implementation"})

def vcenter_get_vm_console_screenshot(vm_name: str) -> str:
    """截取虚拟机控制台画面 (Base64)"""
    return _safe_json({"status": "placeholder_for_implementation"})
```

- [ ] **步骤 2: 提交代码**

```bash
git add tools/vcenter_tools_readonly.py
git commit -m "feat(vcenter): implement 17 readonly atomic tools (stubs)"
```

---

### 任务 4: 实现状态变更工具 (B类 - 强制审批)

**涉及文件:**
- 新建: `tools/vcenter_tools_mutating.py`

- [ ] **步骤 1: 编写带 `@requires_approval` 的原子化变更工具**

```python
from tools.approval import requires_approval
from pyVmomi import vim
from .vcenter_client import get_vcenter_connection, get_obj
import json
import time

def _safe_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)

def _wait_for_task(task):
    while True:
        if task.info.state == 'success': return True, task.info.result
        if task.info.state == 'error': return False, task.info.error.msg
        time.sleep(1)

# ---- 维度三：安全变更类 (18-33) ----

@requires_approval(description="开启虚拟机")
def vcenter_power_on_vm(vm_name: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="强制关闭虚拟机")
def vcenter_power_off_vm(vm_name: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="优雅关闭 Guest OS")
def vcenter_shutdown_guest_os(vm_name: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="强制重启虚拟机")
def vcenter_reset_vm(vm_name: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="创建虚拟机快照")
def vcenter_create_vm_snapshot(vm_name: str, snapshot_name: str, desc: str = "") -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="删除指定的虚拟机快照")
def vcenter_remove_vm_snapshot(vm_name: str, snapshot_name: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="删除虚拟机所有快照")
def vcenter_remove_all_vm_snapshots(vm_name: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="热添加虚拟机 CPU")
def vcenter_hot_add_vm_cpu(vm_name: str, target_cores: int) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="热添加虚拟机内存")
def vcenter_hot_add_vm_memory(vm_name: str, target_mb: int) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="扩展虚拟磁盘容量")
def vcenter_expand_vm_disk(vm_name: str, disk_label: str, target_gb: int) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="重新连接虚拟网卡")
def vcenter_connect_vm_nic(vm_name: str, nic_label: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="更改虚拟机网卡 VLAN/PortGroup")
def vcenter_change_vm_network(vm_name: str, nic_label: str, target_network: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="重启虚拟机网卡 (模拟拔插)")
def vcenter_restart_guest_network(vm_name: str, nic_label: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="挂载 ISO 到虚拟机")
def vcenter_mount_iso_to_vm(vm_name: str, datastore_iso_path: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="主机进入维护模式 (触发疏散)")
def vcenter_enter_maintenance_mode(host_name: str) -> str:
    return _safe_json({"status": "placeholder"})

@requires_approval(description="克隆虚拟机")
def vcenter_clone_vm(source_vm: str, new_vm_name: str, target_cluster: str) -> str:
    return _safe_json({"status": "placeholder"})
```

- [ ] **步骤 2: 提交代码**

```bash
git add tools/vcenter_tools_mutating.py
git commit -m "feat(vcenter): implement 16 mutating atomic tools with approval gating (stubs)"
```

---

### 任务 5: 在 `model_tools.py` 动态注册工具集

**涉及文件:**
- 修改: `model_tools.py`

- [ ] **步骤 1: 实现动态加载机制**

为了防止 33 个工具导致 `model_tools.py` 臃肿，我们采用字典遍历加动态导入机制。

```python
# 在 get_tool_definitions() 中添加 vcenter 分支
    if "vcenter" in toolsets:
        import json
        import os
        # 推荐将 33 个工具的 JSON Schema 定义存放在一个单独的 schemas.json 文件中，此处为演示
        vcenter_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "vcenter_get_cluster_overview",
                    "description": "查询集群 CPU/内存总量及使用率，拉取 Triggered Alarms。",
                    "parameters": {"type": "object", "properties": {"cluster_name": {"type": "string"}}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "vcenter_power_on_vm",
                    "description": "开启虚拟机。此操作需要审批。",
                    "parameters": {"type": "object", "properties": {"vm_name": {"type": "string"}}, "required": ["vm_name"]}
                }
            }
            # ... 此处循环加载所有 33 个 schema ...
        ]
        tools.extend(vcenter_schemas)
```

- [ ] **步骤 2: 在 `handle_function_call` 中通过反射调用**

```python
    # 在 handle_function_call() 中
    elif function_name.startswith("vcenter_"):
        import importlib
        try:
            # 动态判断去哪个文件找函数
            if hasattr(importlib.import_module("tools.vcenter_tools_readonly"), function_name):
                vcenter_module = importlib.import_module("tools.vcenter_tools_readonly")
            else:
                vcenter_module = importlib.import_module("tools.vcenter_tools_mutating")
                
            func = getattr(vcenter_module, function_name)
            return func(**args)
        except AttributeError:
            return f'{{"error": "vCenter tool {function_name} not found."}}'
        except Exception as e:
            return f'{{"error": "{str(e)}"}}'
```

- [ ] **步骤 3: 提交代码**

```bash
git add model_tools.py
git commit -m "feat(vcenter): dynamic registration of 33 atomic tools"
```