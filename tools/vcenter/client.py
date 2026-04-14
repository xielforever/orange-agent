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
