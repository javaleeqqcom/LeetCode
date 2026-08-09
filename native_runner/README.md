# Native OJ process manager

This directory contains the Windows-native process/sandbox prototype.  It is
kept separate from `tools/solution_runner.py` so the legacy and candidate
backends can be compared with identical cases.

## Build

From the repository root, using the `py314` Conda environment:

```powershell
conda run -n py314 cmake -S native_runner -B build/native_runner -G Ninja `
  -DCMAKE_CXX_COMPILER=C:/Users/john/anaconda3/envs/py314/Library/mingw-w64/bin/g++.exe
conda run -n py314 cmake --build build/native_runner --config Release
```

The executable is written to `build/native_runner/oj_native_manager.exe` and is
intentionally ignored by Git.

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
