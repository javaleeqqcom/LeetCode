# 基于 embbed_multi_thread_V3，尽量使得 common init 的环境在多线程中仅加载一次
# 可以考虑将 common init 中可共享的代码 与 不可共享的代码分离
# 可共享的对象在不同线程中采用引用复制，内存共享，以减少线程开销