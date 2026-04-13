from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="tools.iter_node_tools", 
    sources=["tools/iter_node_tools.pyx"],
    language="c++"  # <--- 告訴編譯器使用 MSVC 的 C++ 模式，這才能找到 <vector>
)

setup(
    ext_modules=cythonize(
        [ext], 
        annotate=True,
        compiler_directives={'language_level': "3"} # 建議顯式指定 Python 3
    )
)

# 在 LeetCode 目录下运行 ：
# python tools/setup.py build_ext --inplace
