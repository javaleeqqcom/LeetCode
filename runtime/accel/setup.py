"""Build the optional runtime accelerator from the repository root.

Usage: ``python runtime/accel/setup.py build_ext --inplace``
"""

from __future__ import annotations

import os
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, setup


ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)

extensions = [
    Extension(
        "runtime.accel._result_digest",
        [str(ROOT / "runtime" / "accel" / "_result_digest.pyx")],
    )
]

setup(
    name="leetcode-runtime-accel",
    packages=["runtime", "runtime.accel"],
    package_dir={"": "."},
    ext_modules=cythonize(
        extensions,
        annotate=True,
        compiler_directives={"language_level": 3},
    ),
)
