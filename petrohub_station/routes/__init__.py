# routes/__init__.py
import importlib
import pkgutil
from flask import Blueprint

def register_blueprints(app):
    """
    Auto-import all modules in the routes package and register any Blueprint objects.
    """
    package_name = __name__
    package_path = __path__

    for _, module_name, _ in pkgutil.iter_modules(package_path):
        module = importlib.import_module(f"{package_name}.{module_name}")

        for item in dir(module):
            obj = getattr(module, item)
            # ✅ Only register actual Blueprint objects
            if isinstance(obj, Blueprint):
                print(f"🔹 Registering blueprint: {item} from {module_name}")
                app.register_blueprint(obj)
