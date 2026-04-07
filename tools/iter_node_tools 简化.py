
# ---------- SafeIterBase2 ----------
class SafeIterBase2(Generic[T_Node]):
    """
    安全迭代器基类（方案二版本）
    - 操作包装节点（KitBase2 实例）
    - 环检测使用包装节点的哈希（基于原生节点内存地址）
    - 子类需实现 _prepare_next()
    """

    def __init__(self, node: KitBase2[T_Node] = KitBase2(None), early_stop: bool = False):
        """
        Args:
            init_node: 起始包装节点（可为 None）
            early_stop: 遇到重复节点时是否立即停止迭代（环检测时强制停止）
        """
        self._seen: Dict[KitBase2[T_Node], List[KitBase2[T_Node]]] = {}
        self._revisit: List[KitBase2[T_Node]] = []
        self._cur_node: KitBase2[T_Node] = node if isinstance(node,KitBase2) else KitBase2(node) # 必须代入包装类节点
        self._early_stop = early_stop

        if node:
            self._seen[node] = [node]

    @classmethod
    def _getitem(cls,it: Self, index: int ,allowed_null:bool= False) -> KitBase2[T_Node]:
        """
        根据索引获取节点。
        - 如果索引>=有效节点数量，当 allowed_null 为假则抛出 IndexError，否则为真则返回 包装类的 None 节点
        - 如果中途遇到重复节点，仅当 it._early_stop 为真时抛出 IndexError，否则将跳过重复节点（重复节点不计入有效节点数）
        - 其余情况按 iterator 的遍历次序返回节点
        """
        if index < 0:
            raise IndexError("Negative index not supported")

        i = -1
        for i,node in enumerate(it):
            if i == index:
                return node
            
        # 如果迭代因环而停止，抛出异常
        if it._early_stop and it.revisit_nodes:
            raise IndexError(f"Repeated reference detected by index: {it.revisit_nodes[0].visit_index}.")

        # 索引超出范围，若允许 allowed_null 返回空节点
        if allowed_null:
            return KitBase2(None)
        else: # 否则报错
            raise IndexError(f"Index: {index} out of range")

    @classmethod
    def _flatten(cls, it:SafeIterBase2, max_len: int = -1) -> List[KitBase2[T_Node]]:
        """
        安全展开链表，返回包装节点列表。
        默认 max_len = -1，则不会限制展开节点数量
        """
        if 0==max_len: return []
        nodes: List[KitBase2[T_Node]] = [] # 若 Cython 化，可以设置 max_len（非负时）为最大容量
        for cur_len,node in enumerate(it,1): 
            nodes.append(node)
            if cur_len == max_len: # i 是逐一递增的，若 max_len 非负，则必能生效
                break
        return nodes
        
    @classmethod
    def _to_raw_list(cls, kit_nodes: List[KitBase2[T_Node]]) -> List[T_Node]:
        res = [node.raw for node in kit_nodes if node.raw] # 返回原始值
        assert len(res) == len(kit_nodes), "Empty node found during unwrapping, design error or data corrupted!"
        return res
    
    # 其余函数省略

# ---------- IterNext2 ----------
class IterNext2(SafeIterBase2[T_NEXT]):
    """
    链表安全迭代器，继承 SafeIterBase2 实现环检测，自动包装原生节点。
    支持 __getitem__ 和 flatten 方法。
    """

    def __init__(
        self,
        head: ListNodeKitBase[T_NEXT],
        getitem_null_end: bool = False
    ):
        """
        Args:
            head: 链表头节点（包装类实例）
            getitem_null_end: __getitem__ 风格索引越界时返回 None（True）或抛出 IndexError（False）
        """

        super().__init__(node=head if isinstance(head,ListNodeKitBase) else ListNodeKitBase(head),
                        early_stop=True) # 链表不支持跳过，故早停为 True
        self.allowed_null = getitem_null_end

    @property
    def circle_index(self) -> int:
        """获取当前迭代器的环节点索引，若无则返回 -1"""
        if self.revisit_nodes:
            assert 1 == len(self.revisit_nodes), f"链表重复索引理论上不可能超过一次，而实际重复索引数量={len(self.revisit_nodes)}，可能是被非法重置初始节点，重复迭代。"
            return cast(ListNodeKitBase,self.revisit_nodes[0]).visit_index 
        return -1

    def copy(self,reset_index = False) -> Self:
        """注意默认 reset_index=False，即默认不重置索引值"""
        node = ListNodeKitBase(self._cur_node) if reset_index else cast(ListNodeKitBase,self._cur_node)
        return self.__class__(node, self.allowed_null)

    def __getitem__(self, index: int) -> ListNodeKitBase[T_NEXT]:
        """
        根据索引获取节点。
        - 如果索引越界且 allowed_null=True，返回 None
        - 如果遇到环且未达到索引，根据 allowed_null 返回 None 或抛出 IndexError
        """
        return cast( ListNodeKitBase, SafeIterBase2._getitem( self.copy(), index, self.allowed_null ))
    
    def flatten(self, max_len: int = -1) -> Tuple[List[KitBase2[T_NEXT]], int]:
        """
        安全展开链表，返回节点列表和停止索引。当 max_len 为非负值时，则限制输出的长度不大于 max_len。
        :params max_len:
        raw ...
        :return nodes 注意会受到    
        self._early_stop 影响，为真时会跳过重复节点继续展开，为假时遇到重复节点就会停止收集和...
        stop_index < len(nodes) 说明包含重复节点，其下标为 stop_index， 若 因为 max_len 而停止，stop_index = max_len ，否则 stop_index = -1 （包含有效节点恰好为 max_len 个的情况）
        """
        it = self.copy()
        nodes = SafeIterBase2._flatten(it, max_len=max_len)

        stop_index = it.circle_index # 检测到环，则以环节点索引为停止索引
        if -1 == stop_index and it._cur_node: # 未检测到环，但是迭代器没有迭代到空节点
            stop_index = len(nodes) # 说明迭代器因 max_len 限制而停止
        return nodes, stop_index

class ListNodeKitBase(KitBase2[T_NEXT]):
    """ 链表调试增强工具，使用代理模式（安全实现） 用法: link = ListNodeKit(head_node) """
    def __init__(self, node: KitBase2 | T_NEXT | None , visit_index:int = 0):
        super().__init__(node)
        object.__setattr__(self, '_visit_index', visit_index)
       
    def flatten(self: 'ListNodeKitBase[T_NEXT] | T_NEXT | None', max_len: int = -1) -> Tuple[List[KitBase2[T_NEXT]], int]:
        """展开链表（包装节点类），若 max_len 非负则限制展开节点数量不超过 max_len"""
        return IterNext2[T_NEXT](ListNodeKitBase(self),False).flatten(max_len)
        
    def flatten_raw(self: 'ListNodeKitBase[T_NEXT] | T_NEXT | None', max_len: int = -1) -> Tuple[List[T_NEXT], int]:
        """展开链表（原生节点类），若 max_len 非负则限制展开节点数量不超过 max_len"""
        kit_nodes,stop_index = IterNext2[T_NEXT](ListNodeKitBase(self),False).flatten(max_len)
        return SafeIterBase2._to_raw_list(kit_nodes) , stop_index

    @classmethod
    def _to_string(cls, head: Optional[T_NEXT], prep_property: str = "val" , max_len:int = MAX_LEN) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        # 注意要用 unwrap 去包装节点
        nodes, stop_index = ListNodeKitBase(head).flatten( max_len = max_len)       

        str_lst = []
        
        # 环之前的节点（若无环则全部节点）
        for i in range(stop_index if -1 != stop_index else len(nodes)):
            try:
                str_lst.append(_formatted_string(getattr(nodes[i],prep_property)))
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
                    str_lst.append(_formatted_string(getattr(nodes[i],prep_property)))
            
                # 环结束标记
                str_lst.append("^")

        return f"<class 'ListNodeKit'>: [{','.join(str_lst)}]"
    