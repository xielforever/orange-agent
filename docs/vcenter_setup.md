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
