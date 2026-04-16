改进方案：
1. 将来需要改造为 Cython-C （不依赖 C++）以提高可移植性，降低程序大小
   - 迭代过程中去掉包装节点，在Cython中对节点进行二次包装 -> 访问 cache 命中率低
   - 因此需要在迭代器中用数组维护包装节点所需的信息如 node 和 visit_index，内存连续，性能更好
2. SafeIterBase 面向原生节点
   - _seen : 采用 Dict[node,`_revisit 索引`] ，因为 Dict 持有 node 引用（注意 dict 作为Python容器不能容纳 PyObject* 指针！），不会内存泄漏，并且 Dict 的 key() 自带查重，每个引用至多1次，更高效
     - 有重复时 _seen 的 `_revisit 索引` 只保存最小（早）的。
   - _check_safe 参数改为原生节点
   - 因为弃用包装类 KitBase3 删除，将其功能移植到其他类中
   - _revisit 改为 pair(`并查集索引`，`PyObj*`) ，因为有 _seen 持有 node 引用，不会空引用。
     - 务必！不要篡改 _revisit 结构，例如只剩下 `PyObj*` 
     - `并查集索引` 是指 _revisit[i].`并查集索引` ：为 -1 时节点无重复，为 j 时该节点有重复且最早出现在 _revisit 的下标是 j（为 i 时说明 _revisit[i] 被后面重复出现的所指向）
   - 去掉 __iter__ ，__next__（由子类实现），
   - 去掉 _cur_node ，可兼容 二叉树 和链表，不用管初始节点
   - _flatten 改为仅输出原生节点，而重复信息则需通过 SafeIterBase._revisit 相关属性函数提取
   - _getitem 容易引起歧义，因为会影响迭代器的状态，因此更名为 _get_next(t) 以表示会相当于 next() t 次取节点值。
3. 迭代节点惰性包装化 —— visit_index 的设计
   - visit_index 本质是为了检测重复节点的 from 和 self 位置，其实不需要用包装节点保存，可以根据整体推导
   - 3.1 对于链表，继承 SafeIterBase 的 LinkIterBase 类：`_revisit 索引` 就是 visit_index，因此 visit_index 写成 property 从 _seen[node] 中读取即可
   - 3.2 对于二叉树，继承 SafeIterBase 的 TreeIterBase 类：
     - 3.a 基础版，用一个 List[int] 保存，长度与 _revisit 严格同步，因为用了 list，性能稍差
     - 3.b 静态链表版，用 visit_link: vector[struct(前驱,小端,depth)] 保存，长度与 _revisit 严格同步：
       - `小端` 为 `bitlen` 比特无符号整型
       - 对于第 i 号节点的 visit_index 的值记为 visit_index(i)，则：
         - 当 visit_link[i].前驱 == -1 时：visit_index(i) = visit_link[i].小端
         - 否则：visit_index(i) = visit_link[i].小端 + visit_index(visit_link[i].前驱) << (visit_link[i].depth % bitlen)
       - 而实现 visit_index(j) = visit_index(i) << 1 只需要：
         - 当 visit_link[i].depth % bitlen > 0 ，小端 <<=2 ，visit_link[i].depth++ 即可，其余不变
         - 否则 visit_link[j]=i （表示前驱），小端 = 0，visit_link[i].depth++
       - 至于 visit_index(i)|=1 （右子树）的情况，只需 小端|=1 即可。
       - 如此可实现遍历过程中 O(1) 复杂度（除了扩容的情况，但list也同样避免不了），至于转换为 int，用静态链表内存紧凑不会太慢。
     - 可先用基础版跑通，日后再改进阶的
   - LinkIterBase 的 next、TreeIterBase 的 left、right 等在访问时就执行 _check_safe，从根本上杜绝重复迭代
4. 内部迭代类
   - LinkIterBase 和 TreeIterBase 实现 __iter__ __next__
   - 原 HeapIter 删除，完全没必要用迭代，改为直接在 get_heap 操作 TreeIterBase
   - 将来可以考虑将 LinkIterBase、TreeIterBase、SafeIterBase 都写成 .c 的接口，供 Cython 调用。
   - 目前先用 Cython C++ 跑通
   - _flatten、get_next 在 LinkIterBase 中可以用 _revisit 实现，get_next 只需检查 idx 是否超过 _revisit.size 不够就继续迭代补充
   - 要特别注意的是！TreeIterBase 中 _flatten、get_next 不能以 _revisit 来实现！因为中序、后序遍历等 check_safe 的顺序和遍历顺序不一致，需要额外增加 iter_out: vector<`_revisit的索引`> 来实现。
   - TreeIterBase
     - flatten_* 提供 raw 版（调用 SafeIterBase 即可）和 含visit_index版（需重写函数，并返回重复节点的 vid 序列，否则标定 visit_index 没多大意义）
     - get_next* 也提供 raw 和 visit_index版
5. 面向用户包装的迭代类 TreeIterKit、LinkIterKit
   - 负责调用上述函数，用户友好
   - 将原生 node 包装为带 visit_index，迭代时不包装，输出才惰性包装
6. 进一步性能和依赖程度优化：
   - 改用 Cython-C 实现，用 Tempita 实现 array 数组模板结构体
   - 用 Tempita 模拟 SafeIterBase 的泛型，将 _early_stop 、use_queue 等用宏模板编程优化。
   - TreeIterKit 和 LinkIterKit 的 flatten、get_next 通过维护的 temp_iter（相应的 SafeIterBase 子类），实现记忆化。
     - 如先 p1.flatten(5) ，则暂存 Top5 结果，同时维持 temp_iter 状态，若后面需要 p1.get_next(8) 则只需要迭代 temp_iter 3 次。
     - 但是注意若通过 p2 = LinkIterKit(p1).next() 得到的 p2 包装节点，并不继承 p1 的 temp_iter，因为若有环，则视为从 p2 起步，不记忆 p1 的状态。TreeIterKit 同理。
   - 用 unordered_map 替代 dict，用 PyObject* 替代 PyObject
    -  PyObject* 絕對不會自動維持引用計數
    -  因此改用 PyObject* 时必须手动设计引用計數

当前改进：
1. 我已经实现了 LinkIterKit 的Python代码并过测：
```
1. 随机压力测试（10000 轮，最大节点数 100）
   已完成 10000/10000 轮随机测试
随机压力测试通过
```
