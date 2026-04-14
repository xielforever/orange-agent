import re

with open("tools/vcenter_tools_mutating.py", "r") as f:
    content = f.read()

# Replace the import from tools.approval with a custom decorator
new_import = """
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
"""

content = re.sub(r'from tools\.approval import requires_approval\nfrom pyVmomi import vim\nfrom \.vcenter_client import get_vcenter_connection, get_obj\nimport json\nimport time', new_import, content)

with open("tools/vcenter_tools_mutating.py", "w") as f:
    f.write(content)
