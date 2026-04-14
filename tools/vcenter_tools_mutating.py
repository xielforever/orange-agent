
from pyVmomi import vim
from .vcenter_client import get_vcenter_connection, get_obj
import json
import time

def requires_approval(description):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                from tools.approval import prompt_dangerous_approval
                # Just formatting a string representing the call
                call_str = f"{func.__name__}({args}, {kwargs})"
                res = prompt_dangerous_approval(call_str, description)
                if res not in ('y', 'a'):
                    return _safe_json({"status": "rejected", "message": "User rejected the operation."})
            except ImportError:
                pass
            return func(*args, **kwargs)
        # Copy name and doc
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        
        # Important for inspect.signature
        import functools
        wrapper = functools.wraps(func)(wrapper)
        
        return wrapper
    return decorator


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

# ==============================================================================
# Auto-Registration
# ==============================================================================
import sys
import inspect
from tools.registry import registry

def _register_mutating_tools():
    current_module = sys.modules[__name__]
    for name, func in inspect.getmembers(current_module, inspect.isfunction):
        if name.startswith("vcenter_"):
            doc = func.__doc__ or f"{name} tool"
            schema = {
                "name": name,
                "description": doc,
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
            sig = inspect.signature(func)
            required = []
            for param_name, param in sig.parameters.items():
                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                schema["parameters"]["properties"][param_name] = {
                    "type": param_type,
                    "description": f"{param_name} parameter"
                }
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
            if required:
                schema["parameters"]["required"] = required
            
            registry.register(
                name=name,
                toolset="vcenter",
                schema=schema,
                handler=func,
                check_fn=lambda quiet=False: (True, ""),
                emoji="⚡",
                description=doc
            )

_register_mutating_tools()
