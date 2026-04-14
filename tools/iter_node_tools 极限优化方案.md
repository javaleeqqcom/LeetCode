拟改进方案思考：
1. SafeIterBase3 面向原生节点
   - 更名为 SafeIterKit
   - readonly list cit_pool: 保存原生 node 节点（不是 TreeIterBase 这种包装节点），或者用 PyObj 指针但手动控制引用数，如此可确保原生节点引用安全
   - cit_pool 只能在 _check_safe 时添加，可通过 seen 查重
   - _check_safe 参数改为原生节点，返回改为 cit_pool 索引，若不安全返回 -1（通常计算机能保存到 node 总数不可能超过有符号位长整型上限）
   - KitBase3 用 cit_pool 的索引代替，_cur_node 就变成 _cur_index
   - _revisit_nodes 就可以与 _revisit_index 合并为 _revisit_US_CT_index （表示分别为 并查集、引用池 的索引）
   - 去掉 __iter__ __next（由其他函数实现）
2. 迭代节点惰性包装化
   - TreeIterBase、LinkIterBase 继承 SafeIterKit 或将 SafeIterKit 作为成员对象
   - LinkIterBase 的 visit_index 用 size_t 即可（节点数不可能超过内存索引数）
   - TreeIterBase 的 visit_index 用 int 兼容大整数
   - LinkIterBase 的 next、TreeIterBase 的 left、right 等在访问时就执行 _check_safe，从根本上杜绝重复迭代
3. 内部迭代类
   - IterNext3 改为 LinkIter
   - TreeIter、LinkIter 实现 __iter__ __next__
   - 原 HeapIter 删除，完全没必要用迭代，改为直接在 get_heap 操作 TreeIterBase
4. 面向用户包装的迭代类 TreeIterKit、LinkIterKit
   - 负责调用上述函数，用户友好
   - 将原生 node 包装为带 visit_index，迭代时不包装，输出才惰性包装
