# 基于 embbed_multi_thread_V3，尽量使得 common init 的环境在多线程中仅加载一次
# 可以考虑将 common init 中可共享的代码 与 不可共享的代码分离
# 可共享的对象在不同线程中采用引用复制，内存共享，以减少线程开销


在 Python 3.14（遵循 PEP 734 子解释器提案）中，types.ModuleType 对象不能通过简单的浅拷贝或深拷贝安全地进行“复制构造”并代入其他解释器。由于子解释器（concurrent.interpreters）处于隔离状态，每个解释器拥有独立的模块缓存 (sys.modules)，对象不可共享，必须重新导入或通过专门的机制在解释器间传输。