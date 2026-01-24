from typing import List

"""
输入
nums =
[3,6,4,-6,2,-4,5,-7,-3,6,3,-4]
标准输出
(12 < None > 1),(0 < 3 > 2),(1 < 6 > 3),(2 < 4 > 4),(3 < -6 > 5),(4 < 2 > 6),(5 < -4 > 7),(6 < 5 > 8),(7 < -7 > 9),(8 < -3 > 10),(9 < 6 > 11),(10 < 3 > 12),(11 < -4 > 0)
dec_t= 6  i= 8
[3,6,4,-6,2,-4,5,-7,-3,6,3,-4]
dec_t= 6  i= 4
[3,6,4,-6,2,-4,5,-10,6,3,-4]
dec_t= 5  i= 4
[3,6,4,-4,-4,5,-10,6,3,-4]
dec_t= 5  i= 8
查看更多
输出
11
预期结果
10
"""
import numpy as np

class minHeap:
    def __init__(self, max_size, arr=None) -> None:
        self.max_size = max_size
        if arr is None:
            self.arr = [None] * (max_size + 1)  # 索引 1 ～ max_size 有效，0 不用
            self.size = 0
        else:
            self.size = len(arr)
            assert self.size <= max_size
            # 堆存储在 arr[1..size]
            self.arr = [None] * (max_size + 1)
            for i in range(self.size):
                self.arr[i + 1] = arr[i]
            # 自底向上建堆
            for i in range(self.size // 2, 0, -1):
                self.adjust(i)

    # 对第 i 号元素向下调整（最小堆）
    def adjust(self, i):
        assert i > 0 and i <= self.size
        j = i << 1  # left child
        if j > self.size:
            return
        # 找更小的孩子
        if j + 1 <= self.size and self.arr[j + 1] < self.arr[j]:
            j += 1
        if self.arr[j] < self.arr[i]:
            self.arr[i], self.arr[j] = self.arr[j], self.arr[i]
            self.adjust(j)  # 递归调整

    def push(self, val):
        assert self.size < self.max_size
        self.size += 1
        self.arr[self.size] = val
        # 向上调整
        i = self.size
        while i > 1:
            parent = i >> 1
            if self.arr[parent] <= self.arr[i]:
                break
            self.arr[parent], self.arr[i] = self.arr[i], self.arr[parent]
            i = parent

    def pop(self):
        assert self.size > 0
        top_val = self.arr[1]
        self.arr[1] = self.arr[self.size]
        self.size -= 1
        if self.size > 0:
            self.adjust(1)
        return top_val

    def top(self):
        assert self.size > 0
        return self.arr[1]

    def replace(self, val):
        """替换堆顶并调整"""
        assert self.size > 0
        self.arr[1] = val
        self.adjust(1)

    # 当 size>0 时返回真
    def __bool__(self):
        return self.size > 0

    def print_heap(self, max_line_width=100):
        if self.size == 0:
            print("(empty heap)")
            return

        # Step 1: 转字符串
        strs = []
        for i in range(1, self.size + 1):
            val = self.arr[i]
            s = str(val)
            strs.append(s)
        
        # Step 2: 补全为满二叉树
        import math
        h = math.floor(math.log2(self.size)) + 1
        total_nodes = (1 << h) - 1
        while len(strs) < total_nodes:
            strs.append("")

        # Step 3: 分层
        layers = []
        idx = 0
        for level in range(h):
            num_nodes = 1 << level
            layer = strs[idx:idx + num_nodes]
            layers.append(layer)
            idx += num_nodes

        # Step 4: 自底向上构建显示块（用于树形）
        display_blocks = []  # 每层是一个字符串块列表
        if h >= 1:
            # 最底层
            bottom = layers[-1]
            max_char_width = max(len(s) for s in bottom) if bottom else 1
            gap = 1
            current = [s.rjust(max_char_width) for s in bottom]
            display_blocks.append(current)

            # 向上构建
            for level in range(h - 2, -1, -1):
                parent_layer = layers[level]
                child_blocks = display_blocks[-1]
                new_blocks = []
                for i in range(len(parent_layer)):
                    left = child_blocks[2*i] if 2*i < len(child_blocks) else " "*max_char_width
                    right = child_blocks[2*i+1] if 2*i+1 < len(child_blocks) else " "*max_char_width
                    combined = left + " "*gap + right
                    parent_str = parent_layer[i].rjust(max_char_width) if parent_layer[i] else " "*max_char_width
                    center = len(combined) // 2
                    start = center - len(parent_str) // 2
                    block_list = [" "] * len(combined)
                    for j, ch in enumerate(parent_str):
                        if 0 <= start + j < len(block_list):
                            block_list[start + j] = ch
                    new_blocks.append("".join(block_list))
                display_blocks.append(new_blocks)

            # 反转：display_blocks[0] 是根层
            display_blocks.reverse()

        # Step 5: 决定从哪一层开始切换为列表格式
        switch_level = h  # 默认不切换
        tree_lines = []
        for level in range(h):
            if level < len(display_blocks):
                line = (" " * gap).join(display_blocks[level]).rstrip()
                if len(line) > max_line_width:
                    switch_level = level
                    break
                tree_lines.append(line)
            else:
                # 安全兜底
                switch_level = level
                break

        # Step 6: 打印
        # 上层：树形
        for line in tree_lines:
            print(line)

        # 下层（含 switch_level）：列表格式
        for level in range(switch_level, h):
            real_nodes = []
            start_idx = (1 << level) - 1
            end_idx = min(start_idx + (1 << level), self.size)
            for i in range(start_idx, end_idx):
                real_nodes.append(str(self.arr[i + 1]))  # arr is 1-based
            if real_nodes:
                node_str = ",".join(real_nodes)
                print(f"第{level}层：{node_str}")

inf = int(1e9)

class Node:
    def __init__(self,val,next=0,pre=0) -> None:
        self.val = val
        self.next = next
        self.pre = pre
    
    def __bool__(self):
        return self.val is not None
    
    # 用于鉴别是否为有效节点，当无效时按 default 取值
    def get(self,default=None):
        return self.val if self.val is not None else default
    
    # 用于 print 调试时显示节点信息
    def __str__(self):
        return "({} < {} > {})".format(
            self.pre, self.val, self.next
        )

__DEBUG__ =True

class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        n = len(nums) # 因为每次操作必然减少 nums 的长度，所以记录初始长度
        # 用原位双向链表存储操作后的 nums，索引0表示链表头，其值无效
        link = [Node(None,1,n)]+ [Node(a,i+2 if i<n-1 else 0,i) for i,a in enumerate(nums)]
        if __DEBUG__: print(",".join(map(str,link)))

        def print_link(i):
            out = []
            idx = link[0].next
            while 0!=idx:
                out.append("{}{}".format("^"if idx==i else "",link[idx].val))
                idx = link[idx].next
            print("[{}]".format(",".join(out)))

        # 用小根堆维护相邻和，每次取出最小的进行合并，元素为：（相邻和，左元素link的下标即链表指针）
        H = minHeap(4*n, [(nums[i]+nums[i+1] , i+1) for i in range(n-1)]) 
        # 总相邻递减次数（在循环中更新，当为0时说明nums已经排列为升序）
        dec_times = (np.diff(nums)<0).sum() 
        ans = 0
        while dec_times>0 and H: # 当还有递减次数 且 堆不为空时循环    

            # 判断堆顶是否为有效结果
            i = H.top()[1]
            L = link[i]
            R = link[L.next]
            if not (L and R): # 左右元素已经被删除过，则跳过
                H.pop()
            else: # 有效，先计算操作，再用 replace 替换，减少维护堆的成本
                
                if __DEBUG__: 
                    print('dec_t=',dec_times ," H.size=",H.size)
                    print_link(i)
                    H.print_heap()

                LL_val = link[L.pre].get(-inf) # 用无穷作为哨兵比较递减次数
                RR_val = link[R.next].get(inf) # 用无穷作为哨兵

                # 更新 dec_times（减去变化前的局部递减次数）
                dec_times -= int(LL_val > L.val) + int(L.val>R.val) + int(R.val>RR_val)

                # 更新链表，将 R.val 加到 L.val
                L_val = link[i].val = L.val + R.val
                link[i].next = R.next
                if link[R.next]: 
                    link[R.next].pre = i
                # 删除 R 节点
                R.val = None # 用空值表示被删除

                # 更新 dec_times（加上变化后的局部递减次数）
                dec_times += int(LL_val > L_val) + int(L_val > RR_val)

                assert L_val == L.val

                # 更新堆，首先生成左右相邻的和及其索引（注意越界情况）
                new_items = [] if LL_val <= -inf else [( LL_val + L_val, L.pre)] + [] if RR_val >= inf else [(L_val + RR_val, i)]

                if new_items:
                    H.replace(new_items[0]) # 替换堆顶元素（比先PoP后Push更快）
                    if len(new_items) > 1:
                        H.push(new_items[1]) # 如果存在
                else:
                    H.pop()

                ans += 1
            
        if __DEBUG__: 
            print('dec_t=',dec_times )
            print_link(0)

        return ans

if __DEBUG__:
    obj = Solution()
    nums = [3,6,4,-6,2,-4,5,-7,-3,6,3,-4]
    print(obj.minimumPairRemoval(nums))