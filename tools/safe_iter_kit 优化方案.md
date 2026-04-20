# safe_iter_kit 极限优化方案

## 设计目标

- **Cython‑C 实现**，不依赖 C++ STL（除 `vector`/`deque` 外），提高可移植性。
- **结构统一**：`RevisitEntry` 同时支持链表和二叉树，先向二叉树兼容，后期用宏编程压缩链表内存开销。
- **去 Python 容器**：迭代器内部完全使用 `vector` / `deque` 存储 C 结构，消除 `list`/`deque` 开销。
- **`vid` 内聚**：删除 `vid_list`，所有索引信息存入 `_revisit` 中的 `BigInt`。
- **宏预编译**：最终版本用宏替代  `vector` / `deque` 以及 链表/二叉树 的分支语句，减少运行时开销。

---

## 1. 统一数据结构

### 1.1 `RevisitEntry`（最终版）

```cython
cdef struct BigInt:
    size_t small
    size_t pre
    unsigned short bitLen

cdef struct RevisitEntry:
    size_t uf_index      # 并查集索引，-1 表示首次出现，i 表示重复指向 i
    PyObject* node       # 原生节点指针（不增加引用计数）
    BigInt vid           # 完全二叉树堆索引 / 链表 visit_index
```

- 链表可忽略 `vid`（不访问即可，不影响性能）。
- 二叉树使用 `vid` 存储索引，通过 `small` + `pre` + `bitLen` 实现 O(1) 扩展。

### 1.2 `IterNode`（替代 `NodeStatus` + `queue_vid`/`stack_vid`）

```cython
cdef struct IterNode:
    PyObject* node
    BigInt vid
    bint checked
```

- 用于栈/队列容器，统一保存节点指针、索引和已检查标志。
- **删除** `queue_vid` (Python `deque`) 和 `stack_vid` (Python `list`)。

---

## 2. 容器改造

| 原容器                       | 替换容器                        |
| ---------------------------- | ------------------------------- |
| `cpp_deque[NodeStatus]`      | `deque[IterNode]`               |
| `object queue_vid`           | ❌ 删除（`vid` 在 `IterNode` 中） |
| `vector[NodeStatus]`         | `vector[IterNode]`              |
| `object stack_vid`           | ❌ 删除                          |

### `_push` / `_pop` 示例

```cython
cdef void _push(self, PyObject* node, BigInt vid, bint checked):
    cdef IterNode ele
    ele.node = node
    ele.vid = vid
    ele.checked = checked
    if self.use_queue:
        self.queue.push_back(ele)
    else:
        self.stack.push_back(ele)

cdef IterNode _pop(self):
    if self.use_queue:
        ele = self.queue.front()
        self.queue.pop_front()
    else:
        ele = self.stack.back()
        self.stack.pop_back()
    return ele
```

---

## 3. 删除 `vid_list`

- 原设计：`vid_list` 与 `_revisit` 平行维护。
- **新设计**：`vid` 直接存入 `_revisit[i].vid`，访问时通过 `_revisit[i].vid` 获取。
- 所有需要 `visit_index` 的地方（如 `flatten` 返回值）从 `_revisit` 读取。

---

## 4. `SafeIterBase` 重构（无需泛型）

- 保留 `dict _seen`（Python 字典）自动管理节点引用计数。
- `_revisit` 统一为 `vector[RevisitEntry]`。
- `_check_safe` 返回 `size_t`（首次出现索引）或 `-1`（重复）。
- `_flatten`、`_get_next` 作为静态方法操作迭代器实例。

```cython
cdef class SafeIterBase:
    cdef:
        dict _seen
        vector[RevisitEntry] _revisit
        int repeat_num
        PyObject* _cur
        bint _early_stop
```

---

## 5. `TreeIterBase` 专用优化

- 继承 `SafeIterBase`，增加 `vector[IterNode] stack` 和 `deque[IterNode] queue`。
- `_prepare_next` 中直接操作 `IterNode`，不再访问 Python 容器。
- `flatten` 返回 `(nodes, repeat_indices)`，其中 `nodes` 为 `(vid, 原生节点)` 列表，`repeat_indices` 为 `(重复vid, 指向nodes下标)`。

```cython
cdef tuple flatten(self, Py_ssize_t max_len=-2):
    # 利用 _revisit 和 iter_out_uf_idx 构建输出
    # 完全避免 vid_list
```

---

## 6. `LinkIterBase` 简化

- 无需 `vid`，`_revisit[i].vid` 始终为 0（不访问）。
- `circle_index` 通过 `revisit_nodes[0][0]` 获取。

---

## 7. 性能优化优先级

1. **合并 `queue`/`stack`，删除 Python `list`/`deque`**  
   → 预计提升 >50% 性能。
2. **删除 `vid_list`，统一使用 `_revisit[i].vid`**  
   → 减少内存复制与同步开销。
3. **压缩 `BigInt` 结构**  
   → 使用 `size_t small, pre` 和 `unsigned short bitLen`，减少 cache miss。
4. **（可选）`unordered_map<PyObject*, size_t>` 替换 `dict`**  
   → 需手动管理引用计数（`Py_INCREF`/`Py_DECREF`），仅在极致场景使用。

---

## 8. 最终类层次

```
SafeIterBase (Cython cdef class)
├── LinkIterBase (链表专用，early_stop=True)
└── TreeIterBase (二叉树专用，支持前/中/后/层序)

LinkIterKit (用户包装)
TreeIterKit (用户包装)
```

- 所有迭代器内部无 Python 容器（除 `_seen` 字典外）。
- 包装类 `KitBase` 保持轻量代理模式。

---

## 9. 实施路线

1. **重构 `RevisitEntry` 和 `IterNode`**，删除 `vid_list`。
2. **替换 `queue_checked`/`queue_vid` 为 `deque[IterNode]`**。
3. **替换 `stack_checked`/`stack_vid` 为 `vector[IterNode]`**。
4. **修改 `_push`/`_pop`**，适配新结构。
5. **调整 `_prepare_next`**，直接操作 `IterNode`。
6. **更新 `flatten` 系列方法**，从 `_revisit` 读取 `vid`。
7. **验证链表/二叉树测试**（已有压力测试通过）。
8. **（可选）压缩 `BigInt`** 并优化 `unordered_map`。

---

## 10. 关键约束

- **不引入 C++ STL 依赖**（`vector`/`deque` 除外，Cython 内置）。
- **不增加 Python 对象创建**（迭代过程中不新建 `tuple`/`list`）。
- **保持 `_seen` 字典**以自动管理节点生命周期，避免手动引用计数。
- **早停/跳过重复逻辑**完全由 `_check_safe` 返回值控制。

---
> ✅ 此方案已在 `safe_iter_kit.pyx` 中部分实现（并通过压力测试），后续按上述优先级逐步落地。

## 附录：原生类代码

- 此部分代码不在 safe_iter_kit 中，而是调用 safe_iter_kit，面向用户的接口，也是设计目标的约束。
```py
class ListNode:
    def __init__(self, val:_BASE_TYPE=0, next:Optional[ListNode]=None):
        self.val = val
        self.next = next
    # 方便调试，且与 leetcode 不冲突

    def __repr__(self) -> str:
        return _format_repr( self, _at_id, "val", next=(_at_id,"val") )

# ====== 转换函数 ======
def List2ListNode(lst: List[_BASE_TYPE]) -> Optional[ListNode]:
    head = ListNode(lst[0])
    cur = head
    for val in lst[1:]:
        cur.next = ListNode(val)
        cur = cur.next
    return head

class ListNodeKit(ListNodeKitBase): #[ListNode]):
    """链表调试增强工具，提供安全的扁平化、环检测和打印功能。

    该类基于 ListNodeKitBase 和 ListNodeKitDecorator 实现，
    将原生 ListNode 节点包装为增强对象，保持链式操作的类型一致性。

    主要特性:
        - 空链表判断: 通过 `if link:` 判断是否非空，不支持 `if link is not None`。
        - 索引访问: `link[i]` 返回第 i 个节点的包装对象；长度为 n 的无环链表 link，索引范围为 [0,n]，其中 link[n] 返回空链表，索引越界时抛出 IndexError。
        - 扁平化与环检测: `nodes, cycle_idx = link.flatten()` 返回节点列表和环起始索引(无环为 None)。
        - 字符串表示: `str(link)` 输出带环标记的格式，例如 `[1,2,3,4,5]` 或 `[1,2,3,>4,5^]`(> 表示环起点，^ 表示环尾)。
        - 类型保持: `link.next` 返回的是 ListNodeKit 实例，而非原始节点或 None，便于连续访问。
        - 提取原生节点：`link.node` 返回原生节点 ListNode 对象。

    示例:
    （待添加实例）
    注意:
        - 空链表 (`ListNodeKit(None)`) 无法使用 `next` 属性，访问会抛出 AttributeError。
        - 若链表存在环，索引 n 会迭代 n 次，请优先使用 flatten 检测环。
    """
    def __init__(self, head:ListNodeKitBase|ListNode|None,allowed_null:bool=True):
        super().__init__(head,allowed_null)
    @classmethod
    def from_val(cls, val: _BASE_TYPE) -> 'ListNodeKit':
        """创建单节点树，并设置节点值为 val"""
        return cls(ListNode(val))
    
    def to_str(self, max_len=-1):
        return self._to_string(self, "val", max_len)

    def __repr__(self):
        return self._to_string(self, "val")
    

# 若方法需要返回一个 ListNode，则必须实现 ListNode2List ，以便测试结果的对比。注意该方法进行无环才运行执行
def ListNode2List(node: Optional[ListNode]) -> List[_BASE_TYPE]:
    nodes,it = ListNodeKit(node).flatten()
    assert it.repeat_num > 0, "参数 ListNode 代表的链表有环！"
    return [node.val for node in nodes]

# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val:_BASE_TYPE=0, left:Optional[TreeNode]=None, right:Optional[TreeNode]=None):
        self.val = val
        self.left = left
        self.right = right
    # 方便调试，且与 leetcode 不冲突
    def __repr__(self) -> str:
        return _format_repr( self, _at_id, "val", left=(_at_id,"val") ,right=(_at_id,"val"))
    
# 在 args_parser.py 中添加 TreeNodeKit 类（继承自 TreeNodeKitBase）
class TreeNodeKit(TreeNodeKitBase): #[TreeNode]):
    """
    二叉树调试增强工具，提供安全的层序遍历、环检测和索引访问。
    用法与 ListNodeKit 类似，支持从原始节点或从层序列表构造。
    """
    @classmethod
    def from_level_order(cls, level_order: List[_BASE_TYPE]) -> 'TreeNodeKit':
        """TreeNodeKit.from_level_order(level_order=[1,2,3]) : 从层序列表构建树"""
        from .args_parser import List2TreeNode
        root = List2TreeNode(level_order)
        return cls(root)

    @classmethod
    def from_val(cls, val: _BASE_TYPE) -> 'TreeNodeKit':
        """创建单节点树，并设置节点值为 val"""
        return cls(TreeNode(val))
    
    def to_str(self, max_depth=10, max_node_len=-1, full_traversal=False):
        return self._to_string(self, "val", max_depth, max_node_len, full_traversal)

    def __repr__(self):
        return self._to_string(self, "val")
    
def TreeNode2List(root: Optional[TreeNode]) -> List[_BASE_TYPE]:
    """将 TreeNode 转换为完全二叉树层序列表（含 None 占位）"""
    if not root:
        return []
    
    result = []
    q:Deque[Optional[TreeNode]] = deque([root])
    while q:
        node = q.popleft()
        if node is None:
            result.append(None)
        else:
            result.append(node.val)
            q.append(node.left)
            q.append(node.right)
    
    # 去除尾部多余的 None（保持与输入格式一致）
    while result and result[-1] is None:
        result.pop()
    
    return result
```
