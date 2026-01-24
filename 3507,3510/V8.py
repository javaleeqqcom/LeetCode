"""
执行出错
IndexError: list index out of range
                                      ~~~~^^^^^^^^
    RR_val = inf if -1 == R.next else link[R.next].val
Line 103 in minimumPairRemoval (Solution.py)
    ret = Solution().minimumPairRemoval(param_1)
Line 160 in _driver (Solution.py)
    ~~~~~~~^^
    _driver()
Line 175 in <module> (Solution.py)
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

inf = int(1e9)

class Node:
    def __init__(self,val,next=-1,pre=-1) -> None:
        self.val = val
        self.next = next
        self.pre = pre
    
    def __bool__(self):
        return self.val is not None

__DEBUG__ =True

class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        n = len(nums) # 因为每次操作必然减少 nums 的长度，所以记录初始长度
        # 用原位双向链表存储操作后的 nums
        link = [Node(a,i+1 if i<n else -1,i-1) for i,a in enumerate(nums)]

        # 用小根堆维护相邻和，每次取出最小的进行合并，元素为：（相邻和，左元素link的下标即链表指针）
        H = minHeap(4*n, [(nums[i]+nums[i+1] , i) for i in range(n-1)]) 
        # 总逆序数（在循环中更新，当为0时说明nums已经排列为升序）
        dec_times = (np.diff(nums)<0).sum() 
        ans = 0
        while dec_times>0 : # 当还有逆序数
            
            # 判断堆顶是否为有效结果
            i = H.top()[1]
            L = link[i]
            if L.val is None or L.next == -1: # 左右元素已经被删除过，则跳过
                H.pop()
            else: # 有效，先计算操作，再用 replace 替换，减少维护堆的成本
                R = link[L.next]
                LL_val = -inf if -1 == L.pre else link[L.pre].val # 用无穷作为哨兵比较逆序数
                RR_val = inf if -1 == R.next else link[R.next].val

                # 更新 dec_times（减去变化前的局部逆序数）
                dec_times -= int(LL_val > L) + int(L.val>R.val) + int(R.val>RR_val)

                # 删除 R 节点
                link[L.next].val = None # 用空值表示被删除
                link[L.next].pre = link[L.next].next = -1
                # 更新链表，将 R.val 加到 L.val
                L_val = link[i].val = L.val + R.val
                link[i].next = R.next
                if R.next != -1: link[R.next].pre = i

                # L相当于形参，修改了link[i]后，L不会变化，故在编程时删除L节点，以防止误用旧数据L，等正式代码可剔除
                if __DEBUG__: L.val = None 

                # 更新 dec_times（加上变化后的局部逆序数）
                dec_times += int(LL_val > L_val) + int(L_val > RR_val)

                # 更新堆，首先生成左右相邻的和及其索引（注意越界情况）
                new_items = [] if LL_val <= -inf else [( LL_val + L_val, L.pre)] + [] if RR_val >= inf else [(L_val + RR_val, i)]

                # new_items[0] 一定存在！否则 dec_times == 0 已经跳出循环
                assert new_items
                H.replace(new_items[0]) # 替换堆顶元素（比先PoP后Push更快）
                if len(new_items) > 1:
                    H.push(new_items[1]) # 如果存在

                ans += 1
            
        return ans

