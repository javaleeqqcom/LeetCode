但是我的需求是要将整个 *NodeKit 也纳入 Cython 加速。因为包装节点也是Python引用，这会导致速度减慢。因此在 SafeIterBase 中用 C 结构体 模拟包装节点，等最后输出时再转为 Python 类对象？
而结构体节点信息则存在 _revisit 数组中，绕过 Python Object 的内存管理，当 it_res 对象析构时再回收。
其中 ListNodeKitBase 需要拆分为 ListBase （对应 TreeBase ）实现 visit_index。
*NodeKitBase 等保持 Python 包装，而 *Base 和 IterBase 都转化为Python，并且 *Base 改为结构体，绕开Python类对象都高消耗凑做，用 _revisit 数组保存，在销毁时回收。

其中 TreeBase 结构体及其 visit_index 用如下结构代替：
```
struct BaseIterStruct :
 raw: 用于索引Python节点
 repete_visit:int =-1 指向重复节点的_revisit 的下标（无重复时为-1），自己就是重复则为自己的下标（参考 for i,(p,node) in _revisit: if i==p）

struct TreeIterStruct :
 base BaseIterStruct:
 bit_len: 总二进制位数 （可以推导出树节点深度）
 small_visit: 小端数值
 next_visit:int 高位后继，指向高位公共节点的_revisit 的下标（可以通过 bit_len 计算总链表长度，因此无需额外存储链表长度）
```
类似地结构可以很方便的实现：
1. 大整数+-小整数
2. 大整数 << 或 >>
3. 并且对于树的遍历，当一个节点的小端爆满时，其子树都可以 next 到该节点的 LargeLinkInteger，节约内存开销。
4. 因为绕开了Python引用的内存跳跃，而且在 SafeIterBase 中的 _revisit 中连续，因此可以极大的加速 iterator。

由于树遍历比较复杂，请先实现 ListNodeKitBase 的 Cython 化
1. 定义 BaseIterStruct 结构体，用于 SafeIterBase 遍历使用。以便将 LinkIterStruct 和 TreeIterStruct 共用同一个 get_node_id 函数（取第一个位置的 PyObject 的 id() ）
2. 定义 LinkIterStruct 结构体，包含 base BaseIterStruct 和 _visit_index （计算机位长度有符号整数）。
3. 实现 get_node_id , ... , get_LinkIterNext(LinkIterStruct)->LinkIterStruct 方法（原 next），而 flatten 则由 cdef class ListNodeKitBase 调用 SafeIterBase 的 _flatten 即可，无需重复包装。
独立实现完整地链表遍历类 ListNodeKitBase 通过压力测试后，再考虑实现 TreeNodeKitBase，但是设计的架构需能兼容后者。

请先实现 SafeIterBase 类，框架如下：
```pyx

cdef struct BaseIterStruct:
    PyObject* raw
    Py_ssize_t revisit_idx


cdef struct LinkIterStruct:
    BaseIterStruct base
    Py_ssize_t visit_index

cdef struct Array:
    Py_ssize_t capacity
    Py_ssize_t size
    void* array

cpdef append_array(Array* arr, void* value ,Py_ssize_t sizeof_val):
    ...

cpdef get_array(Array* arr, Py_ssize_t index ,Py_ssize_t sizeof_val):
    ...

cdef struct TreeIterStruct:
    BaseIterStruct base
    Array visit_index # 小端存储，方便 <<1 大概率仅需修改 long_visit_index[0]

# =========================
# 工具函数
# =========================

cdef inline uintptr_t get_ptr(BaseIterStruct* iter_struct):
    return <uintptr_t>iter_struct.raw

cdef PyObject* get_attr_obj(BaseIterStruct* iter_struct, str? attr):
    if iter_struct.raw == NULL:
        return NULL

    cdef object tmp = PyObject_GetAttrString(<object>iter_struct.raw, attr)
    return <PyObject*>tmp

cdef inline LinkIterStruct get_next(LinkIterStruct cur):
    cdef LinkIterStruct nxt

    if cur.base.raw == NULL:
        return make_null()

    nxt.base.raw = get_attr_obj(cur.base, "next")
    nxt.visit_index = cur.visit_index + 1
    nxt.base.revisit_idx = -1

    return nxt

# =========================
# SafeIterBase (Cython)
# =========================

cdef class SafeIterBase:

    cdef void* cur
    cdef dict seen              # uintptr_t -> index
    cdef Array revisit #
    Py_ssize_t sizeof_revisit # 根据 TreeIterStruct 和 LinkIterStruct 选择 sizeof
    cdef Py_ssize_t repeat_num # 注意与 revisit.cap 不等价，仅算 revisit[p] 中 revisit_idx == p 的数量

    cdef cbool early_stop

    def __cinit__(self,  early_stop): # SafeIterBase 不再初始化 cur，由子类实现
        self.seen = {}
        self.repeat_num = 0
        self.revisit # 注意根据 sizeof_revisit

    cdef bint _check_safe(self, void* node):
        cdef uintptr_t rid
        node = <BaseIterStruct>node  # 只关心公共的 BaseIterStruct 部分

        if node.base.raw == NULL:
            return False

        rid = get_ptr(node.base.raw)

        if rid in self.seen:
            node.base.revisit_idx = self.seen[rid]
            self.repeat_num += 1
            return False
        else:
            node.base.revisit_idx = -1
            self.seen[rid] = self.revisit_size
            self._revisit_append(node[0])
            return True

    def get_next(self):
        if self.cur is None:
            raise StopIteration

        # 调用子类实现的 _prepare_next
        res = self._prepare_next()

        if self._early_stop and self.revisit.size: # 出现重复且早停
            self.cur = None

        return res

    def __dealloc__(self):
        if self.revisit != NULL:
            free(self.revisit)

    cpdef tuple flatten(self, Py_ssize_t max_len=-1 , cfun *parse_fun=None):
        """
        返回 (list[node], stop_index)
        """

        cdef list result = []
        cdef BaseIterStruct *cur = self.cur # 遍历时只关心 BaseIterStruct 部分
        cdef Py_ssize_t i = 0
        cdef uintptr_t rid

        if max_len == 0:
            return result, 0

        while cur.base.raw != NULL:
            # 由子类代入的函数，将当前节点转换为最终结果，可以实现：1. 返回原生节点；2. 返回包装后的节点（注意Tree和LInk大小不一样）
            result.append(parse_fun(cur))

            if max_len >= 0 and i + 1 == max_len:
                return result, max_len

            cur = get_next(cur)

            if cur.base.raw == NULL:
                return result, -1

            if not self._check_safe(&cur):
                rid = get_ptr(cur.base.raw)
                return result, self.seen[rid]

            i += 1

        return result, -1

```