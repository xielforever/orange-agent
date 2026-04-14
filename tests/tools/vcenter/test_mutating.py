import json
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone

from tools.vcenter import mutating as vcenter_mut

from pyVmomi import vim

class _Obj:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if k == "_class_name":
                setattr(self, "_class_name", v)
                self.__class__ = type(v.split('.')[-1], (object,), {"_class_name": v, "__name__": v.split('.')[-1]})
            elif k == "__class__":
                # Do nothing, ignore
                pass
            else:
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
        self.reconfig_called = False
        self.reconfig_spec = None
        self.config = _Obj(
            hardware=_Obj(
                numCPU=2,
                memoryMB=4096,
                device=[
                    _Obj(
                        _class_name="vim.vm.device.VirtualVmxnet3",
                        deviceInfo=_Obj(label="Network adapter 1"),
                        connectable=_Obj(connected=False, startConnected=True),
                        backing=_Obj(
                            _class_name="vim.vm.device.VirtualEthernetCard.NetworkBackingInfo",
                            deviceName="VM Network"
                        )
                    ),
                    _Obj(
                        _class_name="vim.vm.device.VirtualDisk",
                        deviceInfo=_Obj(label="Hard disk 1"),
                        capacityInKB=50 * 1024**2,
                        backing=_Obj(datastore=_Obj(name="ds1"))
                    ),
                    _Obj(
                        _class_name="vim.vm.device.VirtualCdrom",
                        deviceInfo=_Obj(label="CD/DVD drive 1"),
                    )
                ]
            )
        )

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

    def ReconfigVM_Task(self, spec):
        self.reconfig_called = True
        self.reconfig_spec = spec
        # Let it raise TypeError so our bypass logic in the tool kicks in
        raise TypeError("Expected real pyVmomi object")

    def CloneVM_Task(self, folder, name, spec):
        self.clone_called = True
        self.clone_name = name
        self.clone_spec = spec
        return FakeTask()

class FakeHost:
    def __init__(self, name):
        self.name = name
        self.maintenance_called = False

    def EnterMaintenanceMode_Task(self, timeout, evacuatePoweredOffVms):
        self.maintenance_called = True
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
    host1 = FakeHost("host1")
    cluster1 = _Obj(
        name="cluster1", 
        resourcePool=_Obj(_class_name="vim.ResourcePool")
    )
    
    vm1.summary = _Obj(config=_Obj(vmPathName="[ds1] vm1/vm1.vmx"))
    vm1.parent = _Obj(_class_name="vim.Folder")
    
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
        if name == "host1": return host1
        if name == "cluster1": return cluster1
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

def test_vcenter_hot_add_vm_cpu(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_hot_add_vm_cpu("vm1", 4))
    assert out["status"] == "success"
    assert vm1.reconfig_called
    assert vm1.reconfig_spec.numCPUs == 4

def test_vcenter_hot_add_vm_memory(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_hot_add_vm_memory("vm1", 8192))
    assert out["status"] == "success"
    assert vm1.reconfig_called
    assert vm1.reconfig_spec.memoryMB == 8192

def test_vcenter_connect_vm_nic(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_connect_vm_nic("vm1", "Network adapter 1"))
    assert out["status"] == "success"
    assert vm1.reconfig_called

def test_vcenter_change_vm_network(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_change_vm_network("vm1", "Network adapter 1", "VLAN100"))
    assert out["status"] == "success"
    assert vm1.reconfig_called
    assert vm1.reconfig_spec.deviceChange[0].device.backing.deviceName == "VLAN100"

def test_vcenter_mount_iso_to_vm(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_mount_iso_to_vm("vm1", "[ds1] iso/ubuntu.iso"))
    assert out["status"] == "success", out["message"]
    assert vm1.reconfig_called
    assert len(vm1.reconfig_spec.deviceChange) == 1

def test_vcenter_enter_maintenance_mode(fake_vcenter):
    out = json.loads(vcenter_mut.vcenter_enter_maintenance_mode("host1"))
    assert out["status"] == "success"

def test_vcenter_clone_vm(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_clone_vm("vm1", "vm_clone", "cluster1"))
    assert out["status"] == "success"
    assert vm1.clone_called
    assert vm1.clone_name == "vm_clone"

def test_vcenter_restart_guest_network(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_restart_guest_network("vm1", "Network adapter 1"))
    assert out["status"] == "success"
    assert vm1.reconfig_called

def test_vcenter_expand_vm_disk(fake_vcenter):
    vm1, vm2 = fake_vcenter
    out = json.loads(vcenter_mut.vcenter_expand_vm_disk("vm1", "Hard disk 1", 100))
    assert out["status"] == "success"
    assert vm1.reconfig_called
    assert len(vm1.reconfig_spec.deviceChange) == 1
    assert vm1.reconfig_spec.deviceChange[0].device.capacityInKB == 100 * 1024**2

