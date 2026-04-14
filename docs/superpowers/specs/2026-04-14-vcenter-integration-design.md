# Design Spec: vCenter AIOps Assistant for Hermes Agent

## 1. Overview
This document specifies the design for extending Hermes Agent with native VMware vCenter management capabilities. The goal is to create an "AIOps Assistant" that can autonomously perform read-only infrastructure inspections, log analysis, and execute high-risk operations (e.g., power management, snapshots) strictly gated by an approval workflow.

## 2. Architecture & Approach
We will use **Approach 1: Native Python Tools with `pyVmomi`**.
This approach involves creating a dedicated toolset within the existing Hermes Agent `tools/` directory.

- **Library**: `pyVmomi` (Official VMware vSphere API Python client).
- **Integration**: Tools will be registered in `model_tools.py` with standard JSON schemas.
- **Security**: 
  - Read-only tools will execute immediately.
  - State-mutating tools will utilize Hermes' native `@requires_approval` or `_approval_notify_sync` mechanism to pause execution and prompt the user via the CLI/Gateway.

## 3. Component Design

### 3.1 Dependencies & Configuration
- **New Dependency**: Add `pyvmomi>=8.0.0` to `requirements.txt`.
- **Environment Variables**:
  - `VCENTER_HOST`: IP or FQDN of the vCenter server.
  - `VCENTER_USER`: Read/Write service account username.
  - `VCENTER_PASSWORD`: Password for the service account.
  - `VCENTER_NO_SSL_VERIFY`: (Optional) Set to `true` to bypass self-signed cert errors.

### 3.2 Core Connection Wrapper
A utility module (`tools/vcenter_client.py`) will be created to manage the connection lifecycle:
- Provide a robust `get_vcenter_connection()` function.
- Handle SSL context and session keep-alives.
- Provide helper functions to recursively search for VM objects by name or UUID.

### 3.3 Tool Definitions (The Actions)
We will create a new file `tools/vcenter_tools.py` containing the following tool functions:

#### Category A: Read-Only (Inspection & Logs) - No Approval Required
1.  **`vcenter_get_vm_status(vm_name: str) -> dict`**
    - **Purpose**: Retrieve CPU, Memory, Power State, and IP address of a specific VM.
2.  **`vcenter_get_cluster_health(cluster_name: Optional[str] = None) -> dict`**
    - **Purpose**: Summarize total resources, usage, and alert status for ESXi hosts in a cluster.
3.  **`vcenter_get_recent_events(vm_name: str, limit: int = 10) -> str`**
    - **Purpose**: Fetch the latest vCenter events/tasks for a VM to diagnose crashes or network drops.

#### Category B: Mutating (State Changes) - Approval Required
1.  **`vcenter_power_manage_vm(vm_name: str, action: str) -> str`**
    - **Purpose**: Turn on, turn off, or restart a VM.
    - **Action values**: `power_on`, `power_off`, `reboot_guest`, `reset`.
    - **Approval**: Triggers Hermes approval prompt before calling `Task.WaitTask`.
2.  **`vcenter_create_snapshot(vm_name: str, snapshot_name: str, description: str) -> str`**
    - **Purpose**: Create a VM snapshot prior to risky operations.
    - **Approval**: Triggers Hermes approval prompt.

### 3.4 Integration with Hermes
1.  **Tool Registration**:
    Update `model_tools.py`:
    - Add the JSON schema definitions for all 5 tools to the `get_tool_definitions()` function under a new `"vcenter"` toolset category.
    - Map the tool names to their corresponding Python functions in `handle_function_call()`.
2.  **Approval Wiring**:
    Ensure the mutating tools utilize the context-aware approval flow. If executed via Gateway, this will naturally push an interactive approval card/message to platforms like Slack, Discord, or Telegram.

## 4. Error Handling & Edge Cases
- **Connection Failures**: If vCenter is unreachable, tools must return a clean JSON error message rather than crashing the Agent thread.
- **Multiple VMs with same name**: The connection wrapper will return an error prompting the LLM to specify the datacenter or UUID if a name collision occurs.
- **Approval Denied**: If the user denies the action, the tool will return `{"status": "cancelled", "reason": "User denied the operation"}` so the LLM knows to stop.

## 5. Security Considerations
- Credentials must never be logged or passed into the LLM context. They remain strictly in the environment variables.
- The `pyVmomi` client will only execute the specific API calls defined in the tools, preventing arbitrary code execution against the vCenter.