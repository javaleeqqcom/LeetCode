# Native OJ process manager

This directory contains the Windows-native process/resource-isolation manager
and the compiled C/C++ worker runtime. It is kept separate from
`tools/solution_runner.py` so all backends can be compared with identical
language-neutral JSON cases.

## Build

`CompiledCppRunner` automatically builds an absent or stale manager with the
selected Windows toolchain. To build it manually, use an x64 Visual Studio
Developer PowerShell:

```powershell
cmake -S native_runner -B build/native_runner-msvc
cmake --build build/native_runner-msvc --config Release
```

The Runtime-managed executable is written to
`build/native_runner/oj_native_manager.exe`; generated managers, student
workers, objects and PDB files are intentionally ignored by Git.

The manager accepts either the backward-compatible Python form
`--python ... --worker-script ...` or a compiled
`--worker-executable ...`. It assigns every child process to the same Job
Object before resuming it.

## Compiled worker runtime

`include/oj_cpp_worker_runtime.hpp` maps `.ojbin` v1/v2 read-only, decodes one
JSON record at a time, invokes the generated adapter, compares `expected`, and
writes a compact summary. Correct v2 cases reuse the precomputed digest;
wrong/error/no-expected cases return only the values needed for Python to
calculate the compatibility digest.

`include/nlohmann/json.hpp` is the official nlohmann/json v3.12.0 single-header
release. See `THIRD_PARTY_NOTICES.md` for source, license and checksum.

## Current security boundary

The prototype creates every Python worker suspended, assigns it to a Windows
Job Object, then resumes it.  The Job Object currently enforces:

- kill all workers when the manager closes;
- at most the requested worker count (hard API limit: 16);
- a per-process committed-memory limit;
- whole-batch timeout termination.

It does **not** yet claim filesystem or network isolation.  Those require a
restricted token/AppContainer plus a dedicated workspace ACL.  Merely changing
the working directory is not a sandbox.
