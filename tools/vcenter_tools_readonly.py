import json
from pyVmomi import vim
from .vcenter_client import get_vcenter_connection, get_obj

def _safe_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)

def _get_content():
    si = get_vcenter_connection()
    return si.RetrieveContent()

def _iter_objects(content, vimtypes):
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtypes, True)
    try:
        return list(container.view)
    finally:
        try:
            container.Destroy()
        except Exception:
            pass

def _iso(dt):
    if dt is None:
        return None
    try:
        return dt.isoformat()
    except Exception:
        return str(dt)

def _bytes_to_gb(value):
    if value is None:
        return None
    return int(round(value / (1024**3)))

def _bytes_to_mb(value):
    if value is None:
        return None
    return int(round(value / (1024**2)))

# ---- 维度一：全局巡检类 (1-7) ----
def vcenter_get_cluster_overview(cluster_name: str = None) -> str:
    """查询集群 CPU/内存总量及使用率"""
    content = _get_content()
    clusters = _iter_objects(content, [vim.ClusterComputeResource])
    if cluster_name:
        clusters = [c for c in clusters if getattr(c, "name", None) == cluster_name]
    result = []
    for c in clusters:
        summary = getattr(c, "summary", None)
        quick = getattr(summary, "quickStats", None)
        triggered = getattr(c, "triggeredAlarmState", []) or []
        result.append(
            {
                "name": getattr(c, "name", None),
                "num_hosts": getattr(summary, "numHosts", None) if summary else None,
                "cpu_total_mhz": getattr(summary, "totalCpu", None) if summary else None,
                "cpu_used_mhz": getattr(quick, "overallCpuUsage", None) if quick else None,
                "memory_total_mb": _bytes_to_mb(getattr(summary, "totalMemory", None)) if summary else None,
                "memory_used_mb": getattr(quick, "overallMemoryUsage", None) if quick else None,
                "triggered_alarms": [
                    {
                        "name": getattr(getattr(getattr(a, "alarm", None), "info", None), "name", None),
                        "status": str(getattr(a, "overallStatus", "")),
                    }
                    for a in triggered
                ],
            }
        )
    return _safe_json({"clusters": result})

def vcenter_get_datastore_capacity() -> str:
    """扫描存储池返回容量及剩余百分比"""
    content = _get_content()
    datastores = _iter_objects(content, [vim.Datastore])
    result = []
    for ds in datastores:
        summary = getattr(ds, "summary", None)
        capacity = getattr(summary, "capacity", None) if summary else None
        free = getattr(summary, "freeSpace", None) if summary else None
        free_pct = None
        if capacity and free is not None:
            try:
                free_pct = round((free / capacity) * 100, 1)
            except Exception:
                free_pct = None
        result.append(
            {
                "name": getattr(ds, "name", None),
                "type": getattr(summary, "type", None) if summary else None,
                "capacity_gb": _bytes_to_gb(capacity),
                "free_gb": _bytes_to_gb(free),
                "free_pct": free_pct,
            }
        )
    return _safe_json({"datastores": result})

def vcenter_get_recent_critical_events(limit: int = 10) -> str:
    """抓取全局 Error/Warning 事件"""
    content = _get_content()
    try:
        events = content.eventManager.QueryEvents(None)
    except Exception:
        events = []

    filtered = []
    for e in events or []:
        sev = getattr(e, "severity", None)
        if sev is None:
            sev = getattr(getattr(e, "info", None), "level", None)
        sev = (sev or "").lower()
        if sev not in {"error", "warning"}:
            continue
        filtered.append(e)

    filtered.sort(key=lambda e: getattr(e, "createdTime", None) or 0, reverse=True)
    filtered = filtered[: max(0, int(limit or 0))]

    result = []
    for e in filtered:
        sev = (getattr(e, "severity", None) or getattr(getattr(e, "info", None), "level", "") or "").lower()
        result.append(
            {
                "created_time": _iso(getattr(e, "createdTime", None)),
                "severity": sev,
                "message": getattr(e, "fullFormattedMessage", None),
            }
        )
    return _safe_json({"events": result})

def vcenter_get_top_cpu_vms(limit: int = 5) -> str:
    """获取 CPU 消耗 Top N 虚拟机"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])

    ranked = []
    for vm in vms:
        summary = getattr(vm, "summary", None)
        quick = getattr(summary, "quickStats", None) if summary else None
        quick = quick or getattr(vm, "quickStats", None)
        cpu = getattr(quick, "overallCpuUsage", None) if quick else None
        ranked.append((cpu if cpu is not None else -1, vm))

    ranked.sort(key=lambda x: x[0], reverse=True)
    n = max(0, int(limit or 0))
    ranked = ranked[:n]

    result = []
    for cpu, vm in ranked:
        config = getattr(vm, "config", None)
        guest = getattr(vm, "guest", None)
        runtime = getattr(vm, "runtime", None)
        result.append(
            {
                "name": getattr(vm, "name", None),
                "uuid": getattr(config, "uuid", None) if config else None,
                "power_state": getattr(runtime, "powerState", None) if runtime else None,
                "ip_address": getattr(guest, "ipAddress", None) if guest else None,
                "cpu_usage_mhz": None if cpu == -1 else cpu,
            }
        )

    return _safe_json({"vms": result})

def vcenter_get_top_memory_vms(limit: int = 5) -> str:
    """获取内存消耗 Top N 虚拟机"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])

    ranked = []
    for vm in vms:
        summary = getattr(vm, "summary", None)
        quick = getattr(summary, "quickStats", None) if summary else None
        quick = quick or getattr(vm, "quickStats", None)
        mem = getattr(quick, "guestMemoryUsage", None) if quick else None
        if mem is None and quick is not None:
            mem = getattr(quick, "hostMemoryUsage", None)
        ranked.append((mem if mem is not None else -1, vm))

    ranked.sort(key=lambda x: x[0], reverse=True)
    n = max(0, int(limit or 0))
    ranked = ranked[:n]

    result = []
    for mem, vm in ranked:
        config = getattr(vm, "config", None)
        guest = getattr(vm, "guest", None)
        runtime = getattr(vm, "runtime", None)
        result.append(
            {
                "name": getattr(vm, "name", None),
                "uuid": getattr(config, "uuid", None) if config else None,
                "power_state": getattr(runtime, "powerState", None) if runtime else None,
                "ip_address": getattr(guest, "ipAddress", None) if guest else None,
                "memory_usage_mb": None if mem == -1 else mem,
            }
        )

    return _safe_json({"vms": result})

def vcenter_get_powered_off_vms() -> str:
    """获取所有关机状态的虚拟机"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])
    
    powered_off = []
    for vm in vms:
        runtime = getattr(vm, "runtime", None)
        state = getattr(runtime, "powerState", None) if runtime else None
        if state == vim.VirtualMachine.PowerState.poweredOff:
            powered_off.append({
                "name": getattr(vm, "name", "unknown"),
                "power_state": "poweredOff"
            })
            
    return _safe_json({"vms": powered_off})

def vcenter_get_vm_events_timeline(vm_name: str, hours: int = 24) -> str:
    """获取虚拟机近期事件时间线"""
    content = _get_content()
    try:
        events = content.eventManager.QueryEvents(None)
    except Exception:
        events = []

    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(hours or 24)))

    filtered = []
    for e in events or []:
        vm = getattr(e, "vm", None)
        if vm is None:
            continue
        # Both Event.vm and Event.vm.vm might hold the reference depending on vCenter version
        name = getattr(vm, "name", None)
        if name is None:
            inner_vm = getattr(vm, "vm", None)
            if inner_vm:
                name = getattr(inner_vm, "name", None)
                
        if name != vm_name:
            continue

        ctime = getattr(e, "createdTime", None)
        if ctime and ctime >= cutoff:
            filtered.append(e)

    filtered.sort(key=lambda e: getattr(e, "createdTime", None) or 0, reverse=True)

    result = []
    for e in filtered:
        sev = (getattr(e, "severity", None) or getattr(getattr(e, "info", None), "level", "") or "").lower()
        result.append(
            {
                "created_time": _iso(getattr(e, "createdTime", None)),
                "severity": sev,
                "message": getattr(e, "fullFormattedMessage", None),
            }
        )
        
    return _safe_json({
        "vm_name": vm_name,
        "events": result
    })

# ---- 维度二：深度排障类 (8-17) ----
def vcenter_get_vm_config(vm_name: str) -> str:
    """获取虚拟机基础配置信息"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])
    vm = next((v for v in vms if getattr(v, "name", None) == vm_name), None)
    if vm is None:
        return _safe_json({"error": f"VM not found: {vm_name}"})

    runtime = getattr(vm, "runtime", None)
    config = getattr(vm, "config", None)
    hw = getattr(config, "hardware", None) if config else None
    guest = getattr(vm, "guest", None)
    summary = getattr(vm, "summary", None)
    sconfig = getattr(summary, "config", None) if summary else None

    return _safe_json(
        {
            "name": getattr(vm, "name", None),
            "uuid": getattr(config, "uuid", None) or getattr(sconfig, "uuid", None),
            "power_state": getattr(runtime, "powerState", None) if runtime else None,
            "guest_os": getattr(sconfig, "guestFullName", None) if sconfig else None,
            "ip_address": getattr(guest, "ipAddress", None) if guest else None,
            "tools_status": getattr(guest, "toolsStatus", None) if guest else None,
            "num_cpu": getattr(hw, "numCPU", None) if hw else None,
            "memory_mb": getattr(hw, "memoryMB", None) if hw else None,
        }
    )

def vcenter_get_vm_performance(vm_name: str) -> str:
    """查询 VM 深度性能指标 (Ready, Swap, Balloon)"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])
    vm = next((v for v in vms if getattr(v, "name", None) == vm_name), None)
    if vm is None:
        return _safe_json({"error": f"VM not found: {vm_name}"})

    summary = getattr(vm, "summary", None)
    qs = getattr(summary, "quickStats", None) if summary else None
    
    metrics = {
        "cpu_ready_ms": getattr(qs, "cpuReady", 0) if qs else 0,
        "memory_ballooned_mb": getattr(qs, "balloonedMemory", 0) if qs else 0,
        "memory_swapped_mb": getattr(qs, "swappedMemory", 0) if qs else 0,
        "uptime_seconds": getattr(qs, "uptimeSeconds", 0) if qs else 0,
        "overall_cpu_usage_mhz": getattr(qs, "overallCpuUsage", 0) if qs else 0,
        "overall_memory_usage_mb": getattr(qs, "guestMemoryUsage", 0) if qs else 0
    }
    
    return _safe_json({
        "vm_name": vm_name,
        "metrics": metrics
    })

def vcenter_get_vm_disk_usage(vm_name: str) -> str:
    """查询虚拟机各个磁盘真实占用情况"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])
    vm = next((v for v in vms if getattr(v, "name", None) == vm_name), None)
    if vm is None:
        return _safe_json({"error": f"VM not found: {vm_name}"})

    config = getattr(vm, "config", None)
    hardware = getattr(config, "hardware", None) if config else None
    devices = getattr(hardware, "device", []) if hardware else []

    disks = []
    for dev in devices:
        # Check if it's a virtual disk
        class_name = type(dev).__name__
        fake_class_name = getattr(getattr(dev, "__class__", None), "__name__", "")
        if "VirtualDisk" in class_name or "VirtualDisk" in fake_class_name:
            backing = getattr(dev, "backing", None)
            datastore = getattr(backing, "datastore", None)
            ds_name = getattr(datastore, "name", None) if datastore else None
            info = getattr(dev, "deviceInfo", None)
            label = getattr(info, "label", None) if info else None
            cap_kb = getattr(dev, "capacityInKB", 0)
            
            disks.append({
                "label": label,
                "capacity_gb": int(cap_kb / (1024**2)) if cap_kb else None,
                "datastore": ds_name,
                "file_name": getattr(backing, "fileName", None)
            })

    guest = getattr(vm, "guest", None)
    guest_disks = []
    for g_disk in getattr(guest, "disk", []) or []:
        guest_disks.append({
            "path": getattr(g_disk, "diskPath", None),
            "capacity_gb": _bytes_to_gb(getattr(g_disk, "capacity", None)),
            "free_gb": _bytes_to_gb(getattr(g_disk, "freeSpace", None))
        })

    return _safe_json({
        "vm_name": vm_name,
        "disks": disks,
        "guest_disks": guest_disks
    })

def vcenter_get_vm_network_info(vm_name: str) -> str:
    """查询 VM 的 vNIC 状态和绑定的 PortGroup"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])
    vm = next((v for v in vms if getattr(v, "name", None) == vm_name), None)
    if vm is None:
        return _safe_json({"error": f"VM not found: {vm_name}"})

    config = getattr(vm, "config", None)
    hardware = getattr(config, "hardware", None) if config else None
    devices = getattr(hardware, "device", []) if hardware else []

    networks = []
    for dev in devices:
        is_net = isinstance(dev, vim.vm.device.VirtualEthernetCard) if hasattr(vim.vm.device, "VirtualEthernetCard") else False
        class_name = type(dev).__name__
        fake_class_name = getattr(getattr(dev, "__class__", None), "__name__", "")
        if is_net or "VirtualEthernetCard" in class_name or "Vmxnet" in class_name or "E1000" in class_name or "VirtualEthernetCard" in fake_class_name or "Vmxnet" in fake_class_name or "E1000" in fake_class_name:
            backing = getattr(dev, "backing", None)
            net_name = None
            if hasattr(backing, "network"):
                net_obj = getattr(backing, "network", None)
                if net_obj:
                    net_name = getattr(net_obj, "name", None)
            if not net_name:
                net_name = getattr(backing, "deviceName", None)
                
            info = getattr(dev, "deviceInfo", None)
            label = getattr(info, "label", None) if info else None
            
            networks.append({
                "label": label,
                "mac_address": getattr(dev, "macAddress", None),
                "network_name": net_name,
                "connected": getattr(getattr(dev, "connectable", None), "connected", None)
            })

    guest = getattr(vm, "guest", None)
    guest_nets = []
    for g_net in getattr(guest, "net", []) or []:
        guest_nets.append({
            "mac_address": getattr(g_net, "macAddress", None),
            "ip_addresses": list(getattr(g_net, "ipAddress", []) or []),
            "network": getattr(g_net, "network", None)
        })

    return _safe_json({
        "vm_name": vm_name,
        "networks": networks,
        "guest_networks": guest_nets
    })

def vcenter_get_host_metrics(host_name: str) -> str:
    """查询特定 ESXi 主机实时负载及硬件传感器"""
    content = _get_content()
    hosts = _iter_objects(content, [vim.HostSystem])
    host = next((h for h in hosts if getattr(h, "name", None) == host_name), None)
    if host is None:
        return _safe_json({"error": f"Host not found: {host_name}"})

    summary = getattr(host, "summary", None)
    hw = getattr(summary, "hardware", None) if summary else None
    qs = getattr(summary, "quickStats", None) if summary else None

    return _safe_json({
        "host_name": host_name,
        "vendor": getattr(hw, "vendor", None) if hw else None,
        "model": getattr(hw, "model", None) if hw else None,
        "cpu_model": getattr(hw, "cpuModel", None) if hw else None,
        "cpu_cores": getattr(hw, "numCpuCores", None) if hw else None,
        "cpu_usage_mhz": getattr(qs, "overallCpuUsage", None) if qs else None,
        "memory_total_gb": _bytes_to_gb(getattr(hw, "memorySize", None)) if hw else None,
        "memory_usage_gb": int(getattr(qs, "overallMemoryUsage", 0) / 1024) if qs and getattr(qs, "overallMemoryUsage", None) else None,
        "uptime_sec": getattr(qs, "uptime", None) if qs else None,
    })

def vcenter_get_host_network_topology(host_name: str) -> str:
    """查询宿主机物理网卡及 vSwitch 拓扑"""
    content = _get_content()
    hosts = _iter_objects(content, [vim.HostSystem])
    host = next((h for h in hosts if getattr(h, "name", None) == host_name), None)
    if host is None:
        return _safe_json({"error": f"Host not found: {host_name}"})

    config = getattr(host, "config", None)
    network = getattr(config, "network", None) if config else None

    vswitches = []
    for vsw in getattr(network, "vswitch", []) or []:
        vswitches.append({
            "name": getattr(vsw, "name", None),
            "num_ports": getattr(vsw, "numPorts", None),
            "mtu": getattr(vsw, "mtu", None),
        })

    pnics = []
    for pnic in getattr(network, "pnic", []) or []:
        speed = getattr(pnic, "linkSpeed", None)
        pnics.append({
            "device": getattr(pnic, "device", None),
            "mac": getattr(pnic, "mac", None),
            "speed_mb": getattr(speed, "speedMb", None) if speed else None,
            "duplex": getattr(speed, "duplex", None) if speed else None,
        })

    return _safe_json({
        "host_name": host_name,
        "vswitches": vswitches,
        "pnics": pnics
    })

def vcenter_get_vm_snapshots(vm_name: str) -> str:
    """列出单台 VM 的快照树"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])
    vm = next((v for v in vms if getattr(v, "name", None) == vm_name), None)
    if vm is None:
        return _safe_json({"error": f"VM not found: {vm_name}"})

    snap = getattr(vm, "snapshot", None)
    root = getattr(snap, "rootSnapshotList", None) if snap else None

    def _node(n):
        return {
            "name": getattr(n, "name", None),
            "description": getattr(n, "description", None),
            "create_time": _iso(getattr(n, "createTime", None)),
            "state": getattr(n, "state", None),
            "children": [_node(c) for c in (getattr(n, "childSnapshotList", None) or [])],
        }

    return _safe_json({"vm_name": getattr(vm, "name", None), "snapshots": [_node(n) for n in (root or [])]})

def vcenter_find_orphan_snapshots(days_old: int = 7) -> str:
    """扫描超期大型快照"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])
    
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)
    
    def _traverse_snapshots(snap_tree, vm_name):
        orphans = []
        for node in snap_tree:
            create_time = getattr(node, "createTime", None)
            if create_time and create_time < cutoff:
                orphans.append({
                    "vm_name": vm_name,
                    "snapshot_name": getattr(node, "name", "unknown"),
                    "description": getattr(node, "description", ""),
                    "create_time": create_time.isoformat()
                })
            child_list = getattr(node, "childSnapshotList", [])
            if child_list:
                orphans.extend(_traverse_snapshots(child_list, vm_name))
        return orphans
        
    all_orphans = []
    for vm in vms:
        snap = getattr(vm, "snapshot", None)
        root_list = getattr(snap, "rootSnapshotList", []) if snap else []
        if root_list:
            all_orphans.extend(_traverse_snapshots(root_list, getattr(vm, "name", "unknown")))
            
    return _safe_json({"snapshots": all_orphans})

def vcenter_get_drs_recommendations(cluster_name: str = None) -> str:
    """获取集群 DRS 建议及冲突规则"""
    content = _get_content()
    clusters = _iter_objects(content, [vim.ClusterComputeResource])
    if cluster_name:
        clusters = [c for c in clusters if getattr(c, "name", None) == cluster_name]

    if not clusters:
        return _safe_json({"error": "No clusters found" if not cluster_name else f"Cluster not found: {cluster_name}"})

    cluster = clusters[0]
    recs = []
    for rec in getattr(cluster, "drsRecommendation", []) or []:
        recs.append({
            "key": getattr(rec, "key", None),
            "reason": getattr(rec, "reasonText", None),
            "rating": getattr(rec, "rating", None)
        })

    return _safe_json({
        "cluster_name": getattr(cluster, "name", None),
        "recommendations": recs
    })

def vcenter_get_vm_console_screenshot(vm_name: str) -> str:
    """截取虚拟机控制台画面 (Base64)"""
    content = _get_content()
    vms = _iter_objects(content, [vim.VirtualMachine])
    vm = next((v for v in vms if getattr(v, "name", None) == vm_name), None)
    if vm is None:
        return _safe_json({"error": f"VM not found: {vm_name}"})

    try:
        task = vm.CreateScreenshot_Task()
        success, result = _wait_for_task(task)
        if success:
            return _safe_json({"vm_name": vm_name, "screenshot_path": result})
        else:
            return _safe_json({"error": f"Failed to create screenshot: {result}"})
    except Exception as e:
        # If CreateScreenshot_Task is not mocked or fails, return an error
        return _safe_json({"error": str(e)})

# ==============================================================================
# Auto-Registration
# ==============================================================================
import inspect
from tools.registry import registry

def _register_readonly_tools():
    # Avoid polluting module namespace, find all functions starting with vcenter_
    import sys; current_module = sys.modules[__name__]
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
                emoji="🔍",
                description=doc
            )

_register_readonly_tools()
