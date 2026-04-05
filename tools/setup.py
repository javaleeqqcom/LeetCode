from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="tools.safe_iter_base", # 強制名稱，不含 LeetCode.tools
    sources=["tools/safe_iter_base.pyx"]
)

setup(
    ext_modules=cythonize([ext], annotate=True)
)

# 在 LeetCode 目录下运行 `python tools/setup.py build_ext --inplace`
