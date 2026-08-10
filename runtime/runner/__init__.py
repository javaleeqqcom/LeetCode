"""Execution backends for independent OJ test cases.

Imports are lazy so the lightweight native/PyPy worker does not import the
CPython-specific management backend while bootstrapping.
"""

__all__ = [
    "CaseStoreReader",
    "CaseStoreWriter",
    "PersistentPythonRunner",
    "NativeProcessRunner",
    "CompiledCppRunner",
    "RunMetrics",
    "RunReport",
    "AutoTuneConfig",
    "AutoTuneDecision",
]


def __getattr__(name: str):
    if name in {"CaseStoreReader", "CaseStoreWriter"}:
        from .case_store import CaseStoreReader, CaseStoreWriter

        return {"CaseStoreReader": CaseStoreReader, "CaseStoreWriter": CaseStoreWriter}[name]
    if name in {"RunMetrics", "RunReport"}:
        from .models import RunMetrics, RunReport

        return {"RunMetrics": RunMetrics, "RunReport": RunReport}[name]
    if name in {"AutoTuneConfig", "AutoTuneDecision"}:
        from .auto_tune import AutoTuneConfig, AutoTuneDecision

        return {
            "AutoTuneConfig": AutoTuneConfig,
            "AutoTuneDecision": AutoTuneDecision,
        }[name]
    if name == "PersistentPythonRunner":
        from .persistent_python import PersistentPythonRunner

        return PersistentPythonRunner
    if name == "NativeProcessRunner":
        from .native_process import NativeProcessRunner

        return NativeProcessRunner
    if name == "CompiledCppRunner":
        from .cpp_process import CompiledCppRunner

        return CompiledCppRunner
    raise AttributeError(name)
