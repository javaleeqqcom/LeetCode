# Optional Runtime Accelerator

This package accelerates stable framework hot paths only. Student OJ sources
remain ordinary Python and are never compiled by this build.

Build from the repository root:

```powershell
python runtime/accel/setup.py build_ext --inplace
```

The stable default uses `fallback.py`. Set `OJ_RUNTIME_ACCEL=cython` to opt in
to the ABI-specific `.pyd`; a missing or incompatible extension still falls
back safely. The compiled digest path is experimental because end-to-end
multi-process benchmarks did not show a consistent adoption-level gain over
the optimized Python fast path. Generated C, HTML annotation, build
directories and `.pyd` files are build artifacts and must not be committed.
