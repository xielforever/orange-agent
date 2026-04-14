import json
from datetime import datetime, timedelta, timezone

import pytest

from tools import vcenter_tools_readonly as vcenter_ro


class _Obj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeContainerView:
    def __init__(self, view):
        self.view = view
        self.destroyed = False

    def Destroy(self):
        self.destroyed = True


class FakeViewManager:
    def __init__(self, view_map):
        self._view_map = view_map

    def CreateContainerView(self, root_folder, vimtype, recursive):
        key = tuple(vimtype)
        return FakeContainerView(self._view_map.get(key, []))


class FakeEventManager:
    def __init__(self, events):
        self._events = events

    def QueryEvents(self, filter_spec):
        return list(self._events)


class FakeContent:
    def __init__(self, view_manager, event_manager):
        self.viewManager = view_manager
        self.eventManager = event_manager
        self.rootFolder = object()


class FakeServiceInstance:
    def __init__(self, content):
        self._content = content

    def RetrieveContent(self):
        return self._content


@pytest.fixture()
def fake_si(monkeypatch):
    now = datetime.now(timezone.utc)

    cluster = _Obj(
        name="c1",
        summary=_Obj(
            totalCpu=10000,
            totalMemory=64 * 1024**3,
            numHosts=3,
            quickStats=_Obj(overallCpuUsage=2500, overallMemoryUsage=10 * 1024),
        ),
        triggeredAlarmState=[
            _Obj(alarm=_Obj(info=_Obj(name="Datastore usage on disk")), overallStatus="red"),
        ],
    )

    ds1 = _Obj(
        name="ds1",
        summary=_Obj(capacity=100 * 1024**3, freeSpace=40 * 1024**3, type="VMFS"),
    )

    evt_err = _Obj(createdTime=now, fullFormattedMessage="err", severity="error")
    evt_warn = _Obj(createdTime=now - timedelta(minutes=1), fullFormattedMessage="warn", severity="warning")
    evt_info = _Obj(createdTime=now - timedelta(minutes=2), fullFormattedMessage="info", severity="info")

    vm = _Obj(
        name="vm1",
        runtime=_Obj(powerState="poweredOn"),
        config=_Obj(uuid="uuid-1", hardware=_Obj(numCPU=4, memoryMB=8192)),
        guest=_Obj(ipAddress="10.0.0.1", toolsStatus="toolsOk"),
        summary=_Obj(config=_Obj(guestFullName="Ubuntu Linux", uuid="uuid-1")),
        quickStats=_Obj(overallCpuUsage=120, guestMemoryUsage=2048),
        snapshot=_Obj(
            rootSnapshotList=[
                _Obj(
                    name="s1",
                    description="d1",
                    createTime=now - timedelta(hours=1),
                    state="poweredOff",
                    childSnapshotList=[],
                )
            ]
        ),
    )

    vm2 = _Obj(
        name="vm2",
        runtime=_Obj(powerState="poweredOn"),
        config=_Obj(uuid="uuid-2", hardware=_Obj(numCPU=2, memoryMB=4096)),
        guest=_Obj(ipAddress="10.0.0.2", toolsStatus="toolsOk"),
        summary=_Obj(config=_Obj(guestFullName="Ubuntu Linux", uuid="uuid-2")),
        quickStats=_Obj(overallCpuUsage=500, guestMemoryUsage=1024),
        snapshot=None,
    )

    vm3 = _Obj(
        name="vm3",
        runtime=_Obj(powerState="poweredOn"),
        config=_Obj(uuid="uuid-3", hardware=_Obj(numCPU=8, memoryMB=16384)),
        guest=_Obj(ipAddress="10.0.0.3", toolsStatus="toolsOk"),
        summary=_Obj(config=_Obj(guestFullName="Ubuntu Linux", uuid="uuid-3")),
        quickStats=_Obj(overallCpuUsage=50, guestMemoryUsage=8192),
        snapshot=None,
    )

    view_map = {
        (vcenter_ro.vim.ClusterComputeResource,): [cluster],
        (vcenter_ro.vim.Datastore,): [ds1],
        (vcenter_ro.vim.VirtualMachine,): [vm, vm2, vm3],
    }
    content = FakeContent(FakeViewManager(view_map), FakeEventManager([evt_err, evt_warn, evt_info]))
    si = FakeServiceInstance(content)

    monkeypatch.setattr(vcenter_ro, "get_vcenter_connection", lambda: si)
    return si


def test_vcenter_get_cluster_overview(fake_si):
    out = json.loads(vcenter_ro.vcenter_get_cluster_overview())
    assert "clusters" in out
    assert out["clusters"][0]["name"] == "c1"
    assert out["clusters"][0]["cpu_total_mhz"] == 10000
    assert out["clusters"][0]["cpu_used_mhz"] == 2500
    assert out["clusters"][0]["memory_total_mb"] == 64 * 1024
    assert out["clusters"][0]["memory_used_mb"] == 10 * 1024
    assert out["clusters"][0]["triggered_alarms"][0]["name"] == "Datastore usage on disk"


def test_vcenter_get_datastore_capacity(fake_si):
    out = json.loads(vcenter_ro.vcenter_get_datastore_capacity())
    assert out["datastores"][0]["name"] == "ds1"
    assert out["datastores"][0]["capacity_gb"] == 100
    assert out["datastores"][0]["free_gb"] == 40
    assert out["datastores"][0]["free_pct"] == 40.0


def test_vcenter_get_recent_critical_events(fake_si):
    out = json.loads(vcenter_ro.vcenter_get_recent_critical_events(limit=10))
    assert len(out["events"]) == 2
    assert out["events"][0]["message"] == "err"
    assert out["events"][1]["message"] == "warn"


def test_vcenter_get_vm_config(fake_si):
    out = json.loads(vcenter_ro.vcenter_get_vm_config("vm1"))
    assert out["name"] == "vm1"
    assert out["uuid"] == "uuid-1"
    assert out["power_state"] == "poweredOn"
    assert out["ip_address"] == "10.0.0.1"
    assert out["num_cpu"] == 4
    assert out["memory_mb"] == 8192


def test_vcenter_get_vm_snapshots(fake_si):
    out = json.loads(vcenter_ro.vcenter_get_vm_snapshots("vm1"))
    assert out["vm_name"] == "vm1"
    assert out["snapshots"][0]["name"] == "s1"
    assert out["snapshots"][0]["description"] == "d1"


def test_vcenter_get_top_cpu_vms(fake_si):
    out = json.loads(vcenter_ro.vcenter_get_top_cpu_vms(limit=2))
    assert [v["name"] for v in out["vms"]] == ["vm2", "vm1"]
    assert [v["cpu_usage_mhz"] for v in out["vms"]] == [500, 120]


def test_vcenter_get_top_memory_vms(fake_si):
    out = json.loads(vcenter_ro.vcenter_get_top_memory_vms(limit=2))
    assert [v["name"] for v in out["vms"]] == ["vm3", "vm1"]
    assert [v["memory_usage_mb"] for v in out["vms"]] == [8192, 2048]
