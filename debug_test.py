import json
from tools.vcenter import mutating as vcenter_mut
from tests.tools.vcenter.test_mutating import fake_vcenter, FakeVM, FakeTask, _Obj, FakeSnapshot, FakeSnapshotTree

class DummyMonkeypatch:
    def setattr(self, module, name, val=None):
        if isinstance(module, str):
            pass
        else:
            setattr(module, name, val)

mp = DummyMonkeypatch()
vm1, vm2 = fake_vcenter.__wrapped__(mp)
import tools.approval
tools.approval.prompt_dangerous_approval = lambda call, desc: "y"

print(vcenter_mut.vcenter_expand_vm_disk("vm1", "Hard disk 1", 100))
print(vcenter_mut.vcenter_connect_vm_nic("vm1", "Network adapter 1"))
