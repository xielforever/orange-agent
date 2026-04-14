import json
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from tools import vcenter_tools_mutating as vcenter_mut

class _Obj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class FakeTask:
    def __init__(self, state="success", result=None, error=None):
        self.info = _Obj(state=state, result=result, error=_Obj(msg=error) if error else None)

class FakeVM:
    def __init__(self, name, power_state="poweredOff"):
        self.name = name
        self.runtime = _Obj(powerState=power_state)
        self.power_on_called = False
        self.power_off_called = False
        self.shutdown_called = False
        self.reset_called = False

    def PowerOn(self):
        self.power_on_called = True
        return FakeTask()

    def PowerOff(self):
        self.power_off_called = True
        return FakeTask()

    def ShutdownGuest(self):
        self.shutdown_called = True

    def ResetVM_Task(self):
        self.reset_called = True
        return FakeTask()

    def CreateSnapshot_Task(self, name, description, memory, quiesce):
        self.snapshot_created = name
        return FakeTask()

    def RemoveAllSnapshots_Task(self):
        self.all_snapshots_removed = True
        return FakeTask()

class FakeSnapshotTree:
    def __init__(self, name, snapshot_obj):
        self.name = name
        self.snapshot = snapshot_obj
        self.childSnapshotList = []

class FakeSnapshot:
    def __init__(self):
        self.removed = False

    def RemoveSnapshot_Task(self, removeChildren):
        self.removed = True
        return FakeTask()

@pytest.fixture()
def fake_vcenter(monkeypatch):
    vm1 = FakeVM("vm1", "poweredOff")
    vm2 = FakeVM("vm2", "poweredOn")
    
    s1_obj = FakeSnapshot()
    s2_obj = FakeSnapshot()
    
    t1 = FakeSnapshotTree("snap1", s1_obj)
    t2 = FakeSnapshotTree("snap2", s2_obj)
    t1.childSnapshotList = [t2]
    
    vm2.snapshot = _Obj(rootSnapshotList=[t1])
    vm2.s1_obj = s1_obj
    vm2.s2_obj = s2_obj
    
    def fake_get_obj(content, vimtype, name):
        if name == "vm1": return vm1
        if name == "vm2": return vm2
        return None

    monkeypatch.setattr(vcenter_mut, "get_vcenter_connection", lambda: MagicMock())
    monkeypatch.setattr(vcenter_mut, "get_obj", fake_get_obj)
    
    # Auto-approve for tests
    monkeypatch.setattr("tools.approval.prompt_dangerous_approval", lambda call, desc: "y")
    return vm1, vm2

def test_vcenter_power_on_vm(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_power_on_vm("vm1"))
    assert out["status"] == "success"
    assert vm1.power_on_called

def test_vcenter_power_off_vm(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_power_off_vm("vm2"))
    assert out["status"] == "success"
    assert vm2.power_off_called

def test_vcenter_shutdown_guest_os(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_shutdown_guest_os("vm2"))
    assert out["status"] == "success"
    assert vm2.shutdown_called

def test_vcenter_create_vm_snapshot(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_create_vm_snapshot("vm2", "new_snap", "desc"))
    assert out["status"] == "success"
    assert vm2.snapshot_created == "new_snap"

def test_vcenter_remove_vm_snapshot(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_remove_vm_snapshot("vm2", "snap2"))
    assert out["status"] == "success"
    assert vm2.s2_obj.removed

def test_vcenter_remove_all_vm_snapshots(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_remove_all_vm_snapshots("vm2"))
    assert out["status"] == "success"
    assert vm2.all_snapshots_removed

