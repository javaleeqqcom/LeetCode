from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="tools.listkit", # 強制名稱，不含 LeetCode.tools
    sources=["tools/listkit.pyx"]
)

setup(
    ext_modules=cythonize([ext], annotate=True)
)

# 在 LeetCode 目录下运行 `python tools/setup.py build_ext --inplace`
