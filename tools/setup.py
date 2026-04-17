from setuptools import setup, Extension
from Cython.Build import cythonize

ext = Extension(
    name="tools.safe_iter_kit", 
    sources=["tools/safe_iter_kit.pyx"],
    language="c++",  # <--- 告訴編譯器使用 MSVC 的 C++ 模式，這才能找到 <vector>
    extra_compile_args=["/std:c++17"],   # ✅ 关键
)

ext_link = Extension(
    name="tools.LinkIterKit", 
    sources=["tools/LinkIterKit.pyx"],
    language="c++",  # <--- 告訴編譯器使用 MSVC 的 C++ 模式，這才能找到 <vector>
    extra_compile_args=["/std:c++17"],   # ✅ 关键
)

setup(
    ext_modules=cythonize(
        [ext_link], 
        annotate=True,
        compiler_directives={'language_level': "3"} # 建議顯式指定 Python 3
    )
)

# 在 LeetCode 目录下运行 ：
# python tools/setup.py build_ext --inplace
