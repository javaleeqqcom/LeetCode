from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="safe_iter_base", # 強制名稱，不含 LeetCode.tools
    sources=["safe_iter_base.pyx"]
)

setup(
    ext_modules=cythonize([ext], annotate=True)
)
