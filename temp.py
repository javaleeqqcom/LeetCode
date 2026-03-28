
    def __repr__(self) -> str:
        """安全打印链表，自动标记环（> 和 ^）"""
        nodes, circle_index = self.flatten()
        str_lst = []
        
        # 环之前的节点
        for i in range(circle_index):
            str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
        
        # 有环标记
        if circle_index != -1:
            str_lst.append(">")
        
        # 环之后的节点
        for i in range(circle_index, len(nodes)):
            str_lst.append(_formated_string(getattr(nodes[i],prep_property)))
        
        # 环结束标记
        if circle_index != -1:
            str_lst.append("^")
        
        return f"<ListNodeKit>:[{','.join(str_lst)}]"
    