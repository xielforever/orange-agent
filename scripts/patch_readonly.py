import inspect
from tools.registry import registry
import tools.vcenter.readonly as ro

def _register_readonly():
    for name, func in inspect.getmembers(ro, inspect.isfunction):
        if name.startswith("vcenter_"):
            doc = func.__doc__ or ""
            # Simple schema generation
            schema = {
                "name": name,
                "description": doc,
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
            # Look at parameters
            sig = inspect.signature(func)
            required = []
            for param_name, param in sig.parameters.items():
                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                schema["parameters"]["properties"][param_name] = {"type": param_type}
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
                emoji="🔍"
            )

