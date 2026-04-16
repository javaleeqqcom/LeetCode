# distutils: language = c++
# ===============================
# 基础导入
# ===============================
from cpython.ref cimport PyObject
from libcpp.vector cimport vector
from libcpp.pair cimport pair
from libc.stdint cimport SIZE_MAX

from typing import List,Tuple
__DEBUG__ = True
# ===============================
# C struct（核心）
# ===============================
cdef struct RevisitEntry:
    size_t uf_index
    PyObject* node
cdef _is_null(PyObject* ptr):
    if ptr == NULL: # 防御性编程，虽然统一用 None 指针表达空节点，但以防意外判断 NULL
        return True
    obj = <object>ptr
    # ✅ 关键修复：拦住 None
    if obj is None:
        return True
    return False

cdef enum:
    MAX_SIZE = (<size_t>-1) - 1 # 最大容量
# ===============================
# SafeIterBase
# ===============================
cdef class SafeIterBase:
    cdef:
        dict _seen                 # node -> first_index
        vector[RevisitEntry] _revisit
        int _repeat_num
        PyObject* _cur
        readonly bint _early_stop # 将来改进：做成泛型模板，静态条件
    def __cinit__(self):
        self._seen = {}
        self._repeat_num = 0
        self._cur = <PyObject*>None
        self._early_stop = True
    def __init__(self, bint early_stop=True):
        self._early_stop = early_stop

    @property
    def repeat_num(self):
        return self._repeat_num

    # ===== 核心：重复检测 =====
    cdef bint _check_safe(self,PyObject* node): # node 必须用 Object 而不能用指针，否则无法让 _seen 自动持有
        cdef size_t first_idx
        cdef RevisitEntry entry
        if _is_null(node):
            return False
        key = <object>node # 关键！指针 -> PyObj
        if key in self._seen:
            first_idx = self._seen[key]
            entry.uf_index = first_idx
            entry.node = node      # 存储指针，不增加引用计数
            self._revisit.push_back(entry)
            # 标记首次重复
            if self._revisit[first_idx].uf_index == SIZE_MAX:
                self._revisit[first_idx].uf_index = first_idx
                self._repeat_num += 1
            return False
        else:
            first_idx = self._revisit.size()
            self._seen[key] = first_idx # node 通过 _seen 的引用计数维持不在 SafeIterBase 析构前消亡
            entry.uf_index = SIZE_MAX
            entry.node = node
            self._revisit.push_back(entry)
            if self._revisit.size() >= MAX_SIZE:
                raise RuntimeError("SafeIterBase: Max size exceeded capacity.")
            return True

    # ===== flatten =====
    @staticmethod
    cdef list _flatten(SafeIterBase it, size_t max_len=SIZE_MAX):
        cdef list out = []
        cdef int i = 0
        cdef object node
        for node in it:
            out.append(node)
            i += 1
            if max_len >= 0 and i >= max_len:
                break
        return out
    # ===== get_next =====
    @staticmethod
    cdef object _get_next(SafeIterBase it, Py_ssize_t index, bint allowed_null):
        cdef Py_ssize_t i = 0
        cdef object node
        if index < 0:
            raise IndexError()
        for node in it: # 不用 enumerate 性能更好
            if i == index:
                return node
            i += 1
        # 如果迭代因环而停止，抛出异常
        if it._early_stop and it.repeat_num > 0:
            raise IndexError("Repeated reference detected")
        if allowed_null:
            return None
        else: # 否则报错
            raise IndexError(f"Index: {index} out of range")
    
    def _prepare_next(self):
        """不用检查 self._cur 非空，但需赋值 self._cur 并确保查重安全"""
        raise NotImplementedError("_prepare_next method should be implemented by the SafeIterBase inheritance class.")
    
    def __iter__(self): return self
    def __next__(self):
        cdef PyObject* res
        if _is_null(self._cur):
            raise StopIteration
        res = self._cur
        # 获取 next（Python属性访问）
        self._prepare_next() 
        return <object>res

    @property
    def revisit_nodes(self):
        cdef list result = []
        cdef Py_ssize_t i
        cdef RevisitEntry entry
        # 顯式使用 range，Cython 會優化為 C 循環
        for i in range(self._revisit.size()):
            entry = self._revisit[i]
            if i == <Py_ssize_t>entry.uf_index:
                # 將 PyObject* 轉回 object
                result.append((entry.uf_index,<object>entry.node))
        return result


# ===============================
# KitBase（轻量代理）
# ===============================
cdef class KitBase:
    cdef readonly object raw
    def __cinit__(self):
        self.raw= None
    def __init__(self, object node) -> None:
        self.raw = KitBase.unwrap(node)
    @classmethod
    def unwrap(cls, other):
        """
        提取包装类内部的原始节点。
        - 如果 other 是 KitBase2 子类实例，返回其内部 _node。
        - 否则直接返回 other 本身（可能为 None）。
        """
        if isinstance(other, KitBase):
            return other.raw
        return other
    def __getattr__(self, name: str) -> Any:
        """代理属性访问到原生节点"""
        # 1️⃣ 先查类属性
        attr = getattr(type(self), name, None)
        # 2️⃣ 如果是 data descriptor（有 __set__）
        if hasattr(attr, "__get__"):
            # ✅ 调用 property
            return attr.__get__(self)
        # 3️⃣ 否则走你原来的逻辑
        node = self.raw
        return getattr(node, name)
    def __setattr__(self, name: str, value: Any) -> None:
        # 1️⃣ 先查类属性
        attr = getattr(type(self), name, None)
        # 2️⃣ 如果是 data descriptor（有 __set__）
        if hasattr(attr, "__set__"):
            attr.__set__(self, value)   # ✅ 调用 property setter
            return
        # 3️⃣ 否则走你原来的逻辑
        node = self.raw
        if node is None:
            raise AttributeError(f"Can't set attribute '{name}' on empty node")
        setattr(node, name, KitBase.unwrap(value))
    def __eq__(self, other) -> bool:
        """比较两个包装节点是否包装同一个原生节点"""
        if not isinstance(other,KitBase): return False
        return self.raw is other.raw
    def __ne__(self, other) -> bool:
        return not self.__eq__(other)
    def __bool__(self) -> bool:
        return self.raw is not None

# ===============================
# LinkIterBase
# ===============================
cdef class LinkIterBase(SafeIterBase):
    def __init__(self, object head):
        super().__init__(early_stop = True) # 链表只支持早停，因为无分支，不可跳过重复节点，否则永远都重复死循环
        head = KitBase.unwrap(head)
        if head is not None:
            self._cur = <PyObject*>head
            # ⚠️ 必须先登记 head
            self._check_safe(self._cur)
    # 覆盖 SafeIterBase 基类
    def _prepare_next(self): # 调用前已确保 self._cur 非空
        next_node = getattr(<object>self._cur, "next") # next_node 必须赋值为 PyObject 类型否则会报错：`Storing unsafe C derivative of temporary Python reference`
        self._cur = <PyObject*>next_node
        # 必须确保早停，__next__ 才会检测重复 _cur 不重复
        if not self._check_safe(self._cur): # 经过 _check_safe 后的 next_node 对象确保了引用计数安全
            self._cur = <PyObject*>None
    @property
    def circle_index(self)->int:
        if self._repeat_num > 0:
            return self.revisit_nodes[0][0]
        return -1
    cpdef object get_next(self, Py_ssize_t index , bint allowed_null):
        return SafeIterBase._get_next(self, index, allowed_null)
    cpdef list iter_flatten_raw(self, size_t max_len=SIZE_MAX):
        return SafeIterBase._flatten(self, max_len)
from args_parser_tools import _formated_string # _to_string 需要
# ===============================
# LinkIterKit（用户层）
# ===============================
cdef class LinkIterKit(KitBase):
    cdef bint _allowed_null
    def __cinit__(self):
        self._allowed_null = True
    def __init__(self, object head, bint allowed_null=True):
        KitBase.__init__(self, head)
        self._allowed_null = allowed_null
    def __iter__(self):
        return LinkIterBase(self.raw)
    @property
    def next(self)->'LinkIterKit':
        node = self.raw
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        
        # 关键：返回当前类的实例，保持装饰器效果延续
        return self.__class__(head = node.next)
    @next.setter
    def next(self, value) -> None:
        node = self.raw # 提取原生节点
        if node is None:
            raise AttributeError("Empty node has no 'next' attribute")
        node.next = self.unwrap(value) # 对原生节点赋值需要去包装
    # ===== flatten =====
    cpdef list flatten(self):
        cdef LinkIterBase it = LinkIterBase(self.raw)
        return it.iter_flatten_raw()
    # ===== flatten + stop index =====
    def flatten_stopIDX(self, size_t max_len=SIZE_MAX)->Tuple[List, int]:
        cdef LinkIterBase it = LinkIterBase(self.raw) if isinstance(self, LinkIterKit) else LinkIterBase(self)
        cdef list nodes = it.iter_flatten_raw(max_len)
        if _is_null(it._cur):
            return nodes, it.circle_index
        else:
            return nodes, <int>max_len
    # ===== getitem =====
    def __getitem__(self, int idx):
        cdef LinkIterBase it = LinkIterBase(self.raw)
        return LinkIterKit(it.get_next(<Py_ssize_t>idx, self._allowed_null))
    @classmethod
    def _to_string(cls, head, prep_property: str = "val" , size_t max_len = SIZE_MAX) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = LinkIterKit(head).flatten_stopIDX( max_len = max_len)       
        str_lst = []
        
        # 环之前的节点（若无环则全部节点）
        for i in range(stop_index if -1 != stop_index else len(nodes)):
            try:
                str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
            except:
                raise Exception(f"len(nodes)={len(nodes)}, stop_index={stop_index}, node={nodes[-1]}")
        
        # 有异常终止索引
        if stop_index >= 0:
            if stop_index == len(nodes):
                str_lst.append("...") # 说明链表长度超过最大限制，截断打印
            else: # 说明检测到链表环
                str_lst.append(">")
            
                # 环之后的节点
                for i in range(stop_index, len(nodes)):
                    assert len(nodes)>0,"len(nodes)==0"
                    str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
            
                # 环结束标记
                str_lst.append("^")
        return f"<class 'ListNodeKit'>: [{','.join(str_lst)}]"

# -------------------------- 树的遍历 ------------------------------      
# 如下代码需补全后方可运行！
exit(0)
from libcpp.algorithm cimport lower_bound
from libcpp.deque cimport deque
from collections import deque as pydeque
cdef enum OpCode:
    OP_END = 0
    OP_L   = 1
    OP_R   = 2
    OP_C   = 4
    OP_SHIFT = 4
    OP_U   = 0x44444444

cdef unsigned int str2OpCode(s:str):
    assert len(s) < 4
    cdef unsigned int res = 0
    for c in s.lower()[::-1]:
        res <<= OP_SHIFT
        if c == 'l':
            res |= OP_L
        elif c == 'r':
            res |= OP_R
        elif c == 'c':
            res |= OP_C
        else:
            raise ValueError(f"invalid op: {s}")
    return res

# 定義簡化名稱
ctypedef pair[PyObject*, bint] NodeStatus
cdef class TreeIterBase(SafeIterBase):
    cdef:
        vector[NodeStatus]    stack_checked   # 存储对应的 checked 标志
        deque[NodeStatus]     queue_checked
        list stack_vid      # 与 stack_checked 保持同步 push
        object queue_vid 

        list vid_list           # 存储 visit_index 与 _revisit 保持同步
        unsigned int _ops
        
        size_t _max_depth
        readonly size_t detectable_depth
        bint _instant_updates

    def __cinit__(self):
        self.stack = []
        self.vid_list = []
        self._ops = 0
        self._allowed_null = True
        self.queue_vid = pydeque()
        ...

    def __init__(self, object root, unsigned int ops, bint use_queue, bint early_stop=False, size_t max_depth=SIZE_MAX):
        super().__init__()
        self._ops = ops
        self.use_queue = use_queue
        self._max_depth = max_depth
        root = KitBase.unwrap(root)
        self._push(root,1,False)

    cdef void _push(self, node, int visit_index , bint checked):
        if not node: return # 自动跳过空节点
        depth = visit_index.bit_length()
        if depth > self.detectable_depth:
            self.detectable_depth = <size_t>depth
            if depth > self._max_depth: return
        
        if self.use_queue:
            self.queue_vid.append(visit_index)
            self.queue_checked.push_back(<pair>(<PyObject*>node,checked))
        else:
            self.stack_vid.append(visit_index)
            self.stack_checked.push_back(<pair>(<PyObject*>node,checked))

    cdef int _pop(self, NodeStatus* ele):
        if self.use_queue:
            ele[0] = self.queue_checked.front()
            self.queue_checked.pop_front()
            return self.queue_vid.popleft()
        else:
            ele[0] = self.stack_checked.back()
            self.stack_checked.pop_back()
            return self.stack_vid.pop()

    def is_empty(self):
        if self.use_queue:
            if not self.queue_vid:
                assert self.queue_checked.empty()
                return True
        else:
            ...

    def _prepare_next(self):
        cdef NodeStatus ele
        cdef bint checked
        cdef unsigned int ops

        while True:
            if self.is_empty(): break

            vid = self._pop(&ele)
            node: object = <object>ele.first

            if not checked:
                self.vid_list.append(vid) # _check_safe 无论T/F，_revisit 的容量+1，同步保存 vid。将来改进静态链表大数可直接加入 revisit
                if self._check_safe(ele.first):
                    ops = self._ops   # ✅ 每个节点重新拷贝
                    while ops:
                        if ops&0xF == OP_L:
                            self._push(node.left,vid<<1, False)
                        elif ops&0xF == OP_R:
                            self._push(node.right,(vid<<1)|1, False)
                        else:
                            self._push(node,vid, True)
                        ops >>= OP_SHIFT
                    if not self._instant_updates: # 非即时更新当前节点，继续 POP
                        continue
                elif self._early_stop: break # 不安全且早停，置为空节点
                else: continue # 不安全，继续 POP
            # 已检查安全，或即时更新，设置 POP 节点为当前节点，跳出循环
            self._cur = ele.first
            return
        # 容器空或早停，置为空节点
        self._cur = <PyObject*>(None)

    cdef list flatten_raw(self, size_t max_len = SIZE_MAX):
        return SafeIterBase._flatten(self,max_len)

    cdef tuple flatten(self, size_t max_len = SIZE_MAX):
        """
        按预设迭代次序返回 (遍历列表,重复索引列表)。
        - 遍历列表: [(堆索引, 原生节点),...]
        - 重复索引列表: [(堆索引, 指向遍历列表的索引),...]
        - 重复索引列表与遍历列表的堆索引无交集
        - early_stop、max_depth 需在构造函数中指定
        :param max_len: 遍历最大节点数（-1表示不限制）
        """
        cdef size_t i = 0, j = 0
        cdef RevisitEntry ele
        cdef vector[pair[size_t, size_t]].iterator it
        
        # 预分配容器，避免多次扩容
        cdef vector[pair[size_t, size_t]] nodes_uf_vec
        nodes_uf_vec.reserve(self.repeat_num)
        
        # 假设 nodes 已经由 _flatten 预生成
        nodes = SafeIterBase._flatten(self, max_len)
        repeat_indices = [] # 其容量必定不少于 repeat_num 但无法提前确定

        for i in range(self._revisit.size()):
            ele = self._revisit[i]
            
            # 优化分支逻辑：合并相同行为
            # 只有当 ele.uf_index 为 i 或 SIZE_MAX 时，才执行插入 nodes[j]
            if i == ele.uf_index or ele.uf_index == SIZE_MAX:
                if i == ele.uf_index:
                    nodes_uf_vec.push_back(pair[size_t, size_t](i, j))
                
                nodes[j] = (self.vid_list[i], nodes[i])
                j += 1
            else:
                # 二分查找：nodes_uf_vec 是按 i 递增插入的，天然有序
                it = lower_bound(nodes_uf_vec.begin(), nodes_uf_vec.end(), 
                                pair[size_t, size_t](ele.uf_index, 0))

                assert it != nodes_uf_vec.end() and (*it).first == ele.uf_index
                repeat_indices.append((self.vid_list[i], (*it).second))
                
        return nodes[:j], repeat_indices

    @property
    def rep_nodes_idx(self) -> List[int]:  # 注意是大整数类
        return [self.vid_list[uf_index] for uf_index, node in self.revisit_nodes]

# 新版本删除 HeapIter，直接路由代码量更少

class TreeIterKit(KitBase):
    cdef int heap_index # 将来改为静态链表大整数类，若初始值超过 size_t 范围，则首个 idx 用 vector<size_t> 存储

    """二叉树调试增强工具，提供安全遍历、环检测、美观打印"""
    def __init__(self, node: KitBase|object|None = None, heap_index: int = 1):
        super().__init__(node)
        assert hasattr(self.raw,"left") and hasattr(self.raw,"right"),"The node parameter entered by TreeIterKit must have 'left', 'right'."
        # 可以补充其他必要的类型检查
        self.heap_index = heap_index 

    def get_heap(self, heap_index: int, allowed_null: bool = False) -> 'TreeIterKit':
        """按堆索引获取节点（从1开始），路径断裂或遇环时抛出 IndexError"""
        if heap_index < 1:
            raise IndexError("Heap index cannot be less than 1.")
        cur = self.raw
        seen = set()
        for bit in bin(heap_index)[3:]: # 去掉 '0b1' 从高位向低位迭代
            if cur is None:
                if allowed_null: return None
                raise IndexError(f"The node pointed to by the heap index does not exist, index value: {heap_index}")
            elif cur in seen:
                raise IndexError("The heap index path is in a loop.")
            seen.add(cur)
            if bit == '0': # 左子树
                cur = cur.left
            else:
                cur = cur.right
        return cur

    def __getitem__(self, index: Py_ssize_t) -> 'TreeIterKit':
        """按层序遍历顺序索引（从0开始），返回包装节点"""
        it = self.layer_iter(early_stop=False)
        node = SafeIterBase._get_next(it, index, False)
        assert isinstance(node, TreeIterKit), f"设计错误：SafeIterBase3._getitem 丢失了节点包装类型的保持状态, 实际类型为 {type(node)}"
        return node

    cdef list flatten_raw(self, early,max_len: Py_ssize_t = -1):
        it = TreeIterBase(self.raw,early_stop=early_stop,max_depth=max_depth)
        return SafeIterBase._flatten(it,max_len)

    cdef tuple flatten(self, early_stop: bool = False, size_t max_depth = SIZE_MAX, size_t max_len = SIZE_MAX):
        """
        ... 按层序遍历的来
        """
        it = TreeIterBase(self, str2OpCode("LR"), use_queue=True,
                       early_stop=early_stop, max_depth=max_depth)
        return it.flatten(max_len)

    cdef tuple flatten_raw(self, early_stop: bool = False, size_t max_depth = SIZE_MAX, size_t max_len = SIZE_MAX):
        """
        ... 按层序遍历的来
        """
        it = TreeIterBase(self, str2OpCode("LR"), use_queue=True,
                       early_stop=early_stop, max_depth=max_depth)
        return it.flatten_raw(max_len)

    cdef TreeIterBase layer_iter(self, early_stop: bool = False, size_t max_depth = SIZE_MAX):
        """层序遍历迭代器 (ULR)"""
        return TreeIterBase(self, str2OpCode("LR"), use_queue=True,
                         early_stop=early_stop, max_depth=max_depth)

    cdef TreeIterBase NLR_iter(self, early_stop: bool = False, size_t max_depth = SIZE_MAX):
        """前序遍历迭代器 (NLR) -> 操作字符串 "RLU" """
        return TreeIterBase(self, str2OpCode("RL"), use_queue=False,
                         early_stop=early_stop, max_depth=max_depth)

    cdef TreeIterBase LNR_iter(self, early_stop: bool = False, size_t max_depth = SIZE_MAX):
        """中序遍历迭代器 (LNR) -> 操作字符串 "RCL" """
        return TreeIterBase(self, str2OpCode("RCL"), use_queue=False,
                         early_stop=early_stop, max_depth=max_depth)

    cdef TreeIterBase LRN_iter(self, early_stop: bool = False, size_t max_depth = SIZE_MAX):
        """后序遍历迭代器 (LRN) -> 操作字符串 "CRL" """
        return TreeIterBase(self, str2OpCode("CRL"), use_queue=False,
                         early_stop=early_stop, max_depth=max_depth)

    def __iter__(self):
        return self.layer_iter()

    @staticmethod
    cdef str _to_string(
        object root,
        prep_property: str = "val",
        size_t max_depth = 10, # 10 层已经达到最大 512 个节点，文本量巨大
        size_t max_node_len = SIZE_MAX,
        bint full_traversal = False
    ):
        """
        生成树的字符串表示（树形图 + 索引映射）。
        :param root: 根节点（包装或原生）
        :param prep_property: 取值属性名，如 'val'
        :param max_depth: 最大显示深度
        :param max_node_len: 最多显示节点数（-1无限制）
        :param full_traversal: True则遍历所有节点（跳过重复），False则遇重复停止
        """
        # 未来优化：对于超高层数二叉树，可以分块打印，避免文本量巨大。

        # 因为 _to_string 是类方法，不能依赖 TreeIterKit 对象，最低只需依赖基类 TreeBase
        cdef TreeIterBase it = TreeIterBase(
            root, str2OpCode("LR"), use_queue=True,
            early_stop= <bint>(not full_traversal),
            max_depth = max_depth
        )
        vid_nodes, rep_idx = it.flatten(max_len= max_node_len)

        if not vid_nodes:
            return "<class 'TreeNodeKit'>: empty"


        # 构建重复索引标注
        repeat_mark = {} 
        # 遍历 重复访问索引、指向有效节点索引
        for revisit_index, nodes_idx in rep_idx: 
            repeat_index = vid_nodes[nodes_idx][0]
            repeat_mark[repeat_index] = f"*{repeat_index}" # 可能会重复多次，但无所谓覆盖
            repeat_mark[revisit_index] = f"^{repeat_index}"

        # 收集索引 -> 值
        idx_val = {kn.visit_index: getattr(kn.raw, prep_property) for kn in vid_nodes}

        if not idx_val:
            return "<class 'TreeNodeKit'>: empty"

        max_idx = max(max(idx_val.keys()), max(repeat_mark.keys()) if repeat_mark else 0)
        # 构建层序列表用于 binarytree
        level_list = [""] * max_idx
        for idx, val in idx_val.items():
            level_list[idx - 1] = str(idx)
        for idx, mark in repeat_mark.items():
            level_list[idx - 1] = mark

        # 生成树形图
        try:
            from binarytree import build
            bt = build(level_list)
            tree_str = str(bt) if bt else "null"
        except Exception:
            tree_str = "Error: binarytree build failed"

        parts = []
        repeat_idxs = [kn.visit_index for kn in it.revisit_nodes]
        if full_traversal:
            if repeat_idxs:
                parts.append(f'  "warning_duplicate_idx": {repeat_idxs}')
        else:
            if repeat_idxs:
                assert 1 == len(repeat_idxs), "使用了 full_traversal=False, 但发现重复索引数量 > 1"
                parts.append(f'  "stop_by_duplicate_idx": {repeat_idxs[0]}')

        tree_part = '  "tree_by_idx": """{}{}"""'.format(
            tree_str,
            '...\n' if (it.detectable_depth or it.cur) else ''
        )
        parts.append(tree_part)
        parts.append(f'  "idx:val": {idx_val}')

        body = ",\n".join(parts)
        return f"<class 'TreeNodeKit'>: {{\n{body}\n}}"