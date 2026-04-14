# vCenter AIOps Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend Hermes Agent with native VMware vCenter management capabilities (read-only inspections, log analysis, and approval-gated state mutations) using `pyVmomi`.

**Architecture:** Create a robust vCenter client wrapper, implement 5 specific tool functions (3 read-only, 2 mutating), register their schemas in `model_tools.py`, and wire mutating tools to Hermes' native `_approval_notify_sync` mechanism.

**Tech Stack:** Python 3.11+, `pyvmomi>=8.0.0`, Hermes Agent Tooling Architecture.

---

### Task 1: Add Dependencies and Configuration

**Files:**
- Modify: `requirements.txt`
- Modify: `config.yaml` (example config)

- [ ] **Step 1: Update requirements.txt**

Append `pyvmomi>=8.0.0` to the end of `requirements.txt`.

```text
pyvmomi>=8.0.0
```

- [ ] **Step 2: Document environment variables**

Create a `docs/vcenter_setup.md` file to document the required environment variables for the user.

```markdown
# vCenter Configuration

To enable the vCenter AIOps tools, set the following environment variables:

```bash
export VCENTER_HOST="vcenter.example.com"
export VCENTER_USER="administrator@vsphere.local"
export VCENTER_PASSWORD="your_password"
export VCENTER_NO_SSL_VERIFY="true" # Optional, to bypass SSL cert warnings
```
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt docs/vcenter_setup.md
git commit -m "feat(vcenter): add pyvmomi dependency and configuration docs"
```

---

### Task 2: Implement Core Connection Wrapper

**Files:**
- Create: `tools/vcenter_client.py`

- [ ] **Step 1: Write the vcenter client wrapper**

Create `tools/vcenter_client.py` to handle the connection lifecycle and basic search utilities.

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
            # Simple check to see if session is active
            _vcenter_instance.CurrentTime()
            return _vcenter_instance
        except Exception:
            _vcenter_instance = None

    host = os.getenv("VCENTER_HOST")
    user = os.getenv("VCENTER_USER")
    password = os.getenv("VCENTER_PASSWORD")
    
    if not all([host, user, password]):
        raise ValueError("VCENTER_HOST, VCENTER_USER, and VCENTER_PASSWORD environment variables are required.")

    context = None
    if os.getenv("VCENTER_NO_SSL_VERIFY", "").lower() in ("true", "1", "yes"):
        context = ssl._create_unverified_context()

    try:
        si = SmartConnect(host=host, user=user, pwd=password, sslContext=context)
        _vcenter_instance = si
        return si
    except Exception as e:
        raise ConnectionError(f"Failed to connect to vCenter at {host}: {e}")

def get_obj(content, vimtype, name):
    """
    Return an object by name, if name is None the
    first found object is returned
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

- [ ] **Step 2: Commit**

```bash
git add tools/vcenter_client.py
git commit -m "feat(vcenter): implement core connection wrapper"
```

---

### Task 3: Implement Read-Only Tools (Inspection & Logs)

**Files:**
- Create: `tools/vcenter_tools.py`

- [ ] **Step 1: Implement inspection and log tools**

Create `tools/vcenter_tools.py` and implement the 3 read-only tools.

```python
import json
from datetime import datetime
from .vcenter_client import get_vcenter_connection, get_obj
from pyVmomi import vim

def _safe_json(data):
    try:
        return json.dumps(data, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def vcenter_get_vm_status(vm_name: str) -> str:
    """Retrieve CPU, Memory, Power State, and IP address of a specific VM."""
    try:
        si = get_vcenter_connection()
        vm = get_obj(si.RetrieveContent(), [vim.VirtualMachine], vm_name)
        if not vm:
            return _safe_json({"error": f"VM '{vm_name}' not found."})
        
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
    """Summarize resources and status for ESXi hosts in a cluster."""
    try:
        si = get_vcenter_connection()
        cluster = get_obj(si.RetrieveContent(), [vim.ClusterComputeResource], cluster_name)
        if not cluster and cluster_name:
             return _safe_json({"error": f"Cluster '{cluster_name}' not found."})
        elif not cluster:
            # Fallback to first cluster if none specified and only one exists, 
            # otherwise just get all hosts. Simplified for this spec.
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
    """Fetch the latest vCenter events for a VM."""
    try:
        si = get_vcenter_connection()
        content = si.RetrieveContent()
        vm = get_obj(content, [vim.VirtualMachine], vm_name)
        if not vm:
            return _safe_json({"error": f"VM '{vm_name}' not found."})

        event_manager = content.eventManager
        filter_spec = vim.event.EventFilterSpec()
        entity_spec = vim.event.EventFilterSpec.ByEntity(entity=vm, recursion="self")
        filter_spec.entity = entity_spec
        
        # We must collect events and sort them manually or use EventCollector
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

- [ ] **Step 2: Commit**

```bash
git add tools/vcenter_tools.py
git commit -m "feat(vcenter): implement read-only inspection and log tools"
```

---

### Task 4: Implement Mutating Tools (Power & Snapshots)

**Files:**
- Modify: `tools/vcenter_tools.py`
- Modify: `tools/approval.py` (Verify or ensure `@requires_approval` logic is accessible)

- [ ] **Step 1: Add mutating tools to `tools/vcenter_tools.py`**

Append the mutating functions. Note: We assume the `@requires_approval` decorator from `tools.approval` exists based on the codebase analysis.

```python
# Add this import at the top of tools/vcenter_tools.py
from tools.approval import requires_approval
import time

# Append these functions

def _wait_for_task(task):
    """Waits and provides updates on a vSphere task"""
    task_done = False
    has_errors = False
    while not task_done:
        if task.info.state == 'success':
            return True, task.info.result
        if task.info.state == 'error':
            return False, task.info.error.msg
        time.sleep(1)

@requires_approval(description="Power manage a Virtual Machine (Turn on, off, restart)")
def vcenter_power_manage_vm(vm_name: str, action: str) -> str:
    """Turn on, turn off, or restart a VM."""
    valid_actions = ['power_on', 'power_off', 'reboot_guest', 'reset']
    if action not in valid_actions:
        return _safe_json({"error": f"Invalid action. Must be one of {valid_actions}"})

    try:
        si = get_vcenter_connection()
        vm = get_obj(si.RetrieveContent(), [vim.VirtualMachine], vm_name)
        if not vm:
            return _safe_json({"error": f"VM '{vm_name}' not found."})

        task = None
        if action == 'power_on':
            task = vm.PowerOn()
        elif action == 'power_off':
            task = vm.PowerOff()
        elif action == 'reboot_guest':
            vm.RebootGuest() # This doesn't return a task in the same way
            return _safe_json({"status": "success", "message": f"Guest reboot initiated for {vm_name}"})
        elif action == 'reset':
            task = vm.Reset()

        if task:
            success, result = _wait_for_task(task)
            if success:
                return _safe_json({"status": "success", "message": f"Action '{action}' completed on {vm_name}"})
            else:
                return _safe_json({"error": f"Action '{action}' failed: {result}"})
        
        return _safe_json({"error": "Failed to initiate task"})
    except Exception as e:
        return _safe_json({"error": str(e)})

@requires_approval(description="Create a snapshot of a Virtual Machine")
def vcenter_create_snapshot(vm_name: str, snapshot_name: str, description: str = "") -> str:
    """Create a VM snapshot prior to risky operations."""
    try:
        si = get_vcenter_connection()
        vm = get_obj(si.RetrieveContent(), [vim.VirtualMachine], vm_name)
        if not vm:
            return _safe_json({"error": f"VM '{vm_name}' not found."})

        memory = False
        quiesce = False
        task = vm.CreateSnapshot(snapshot_name, description, memory, quiesce)
        
        success, result = _wait_for_task(task)
        if success:
            return _safe_json({"status": "success", "message": f"Snapshot '{snapshot_name}' created for {vm_name}"})
        else:
            return _safe_json({"error": f"Snapshot creation failed: {result}"})
    except Exception as e:
        return _safe_json({"error": str(e)})
```

- [ ] **Step 2: Commit**

```bash
git add tools/vcenter_tools.py
git commit -m "feat(vcenter): implement mutating tools with approval gating"
```

---

### Task 5: Register Tools in `model_tools.py`

**Files:**
- Modify: `model_tools.py`

- [ ] **Step 1: Import new tools**

At the top of `model_tools.py`, import the new functions.
```python
from tools.vcenter_tools import (
    vcenter_get_vm_status,
    vcenter_get_cluster_health,
    vcenter_get_recent_events,
    vcenter_power_manage_vm,
    vcenter_create_snapshot
)
```

- [ ] **Step 2: Add JSON Schemas to `get_tool_definitions`**

Inside `get_tool_definitions()`, add the `vcenter` toolset logic:

```python
    # ... inside get_tool_definitions ...
    if "vcenter" in toolsets:
        tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "vcenter_get_vm_status",
                    "description": "Retrieve CPU, Memory, Power State, and IP address of a specific VMware Virtual Machine.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vm_name": {"type": "string", "description": "The exact name of the virtual machine"}
                        },
                        "required": ["vm_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "vcenter_get_cluster_health",
                    "description": "Summarize resources and status for ESXi hosts in a VMware cluster.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cluster_name": {"type": "string", "description": "The name of the cluster (optional, leave empty for all hosts)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "vcenter_get_recent_events",
                    "description": "Fetch the latest vCenter events/tasks for a VM to diagnose issues.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vm_name": {"type": "string", "description": "The exact name of the virtual machine"},
                            "limit": {"type": "integer", "description": "Number of events to retrieve (default 10)"}
                        },
                        "required": ["vm_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "vcenter_power_manage_vm",
                    "description": "Turn on, turn off, reboot, or reset a Virtual Machine. This action requires user approval.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vm_name": {"type": "string", "description": "The exact name of the virtual machine"},
                            "action": {
                                "type": "string", 
                                "enum": ["power_on", "power_off", "reboot_guest", "reset"],
                                "description": "The power action to perform"
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
                    "description": "Create a snapshot of a Virtual Machine prior to risky operations. This action requires user approval.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "vm_name": {"type": "string", "description": "The exact name of the virtual machine"},
                            "snapshot_name": {"type": "string", "description": "A short, descriptive name for the snapshot"},
                            "description": {"type": "string", "description": "Detailed description of why the snapshot is being taken"}
                        },
                        "required": ["vm_name", "snapshot_name", "description"]
                    }
                }
            }
        ])
```

- [ ] **Step 3: Map functions in `handle_function_call`**

Inside `handle_function_call()`, add the dispatch routing:

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

- [ ] **Step 4: Commit**

```bash
git add model_tools.py
git commit -m "feat(vcenter): register vcenter tools in model_tools.py"
```
