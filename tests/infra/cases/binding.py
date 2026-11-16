"""Bind a package of model-independent test cases to one model's adapter."""

import importlib
import inspect
import pkgutil
import unittest


def bind_package_cases(package_name, package_path, adapter, namespace):
    """Define in `namespace` a copy of every case class of the package that solves with `adapter`.

    Each case class of each module of the package is re-created as
    `type(name, (adapter, case), ...)`, under the case's own name, in the
    module that calls this, so that the runner can address every test by its
    dotted name.
    """
    for module_info in sorted(pkgutil.iter_modules(package_path), key=lambda info: info.name):
        module = importlib.import_module(f"{package_name}.{module_info.name}")
        for name, case in vars(module).items():
            if inspect.isclass(case) and issubclass(case, unittest.TestCase) and case.__module__ == module.__name__:
                namespace[name] = type(
                    name, (adapter, case), {"__module__": namespace["__name__"], "__doc__": case.__doc__}
                )
