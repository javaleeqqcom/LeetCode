"""
执行出错
OverflowError: Python integer -2971215073 out of bounds for int32
    ~~~^^^^^
    sub[1:3] = a # 合并拷贝成双份，不会破坏逆序数的计算，还能避免硬删除
Line 88 in minimumPairRemoval (Solution.py)
    ret = Solution().minimumPairRemoval(param_1)
Line 129 in _driver (Solution.py)
    ~~~~~~~^^
    _driver()
Line 144 in <module> (Solution.py)
 
标准输出
[(4, 1), (1, 2), (2, 3), (1, 4), (0, 5), (3, 6), (2, 7), (2, 8), (1, 9), (-1, 10)]
最后执行的输入
查看测试用例
nums =
[2,2,-1,3,-2,2,1,1,1,0,-1]
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

# 将 inf 替换为 'INF' 打印
def format_array(arr):
    def format(x):
        if x < inf:
            if x > -inf:
                return "{:4d}".format(x)
            else:
                return "-INF"
        else:
            return " INF"

    return "[{}]".format(",".join(map(format,arr)))

def format_bool(b):
    return "  T " if b else "  F "


class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        n = len(nums) # 因为每次操作必然减少 nums 的长度，所以记录初始长度
        arr = np.array([-inf]+ nums +[inf],dtype=np.int32) # 左右增加哨兵以省略越界判断

        # 用小根堆维护相邻和，每次取出最小的进行合并，元素为：（相邻和，arr的左下标）
        Harr = list(zip( (arr[1:-2] + arr[2:-1]).tolist() ,range(1,n+1) ))
        print(Harr)
        H = minHeap(4*n,Harr) 
        # 总逆序数（在循环中更新，当为0时说明nums已经排列为升序）
        dec_times = (np.diff(nums)<0).sum() 
        retained = np.ones_like(arr,dtype=bool)
        while dec_times>0 and H: # 当还有逆序数且堆不为空时
            print("dec_t={}, top={}".format(dec_times,H.top()))
            print(format_array(arr.tolist()))
            print("[{}]".format(",".join(map(format_bool,retained))))
            # 判断堆顶是否为有效结果
            top = H.top()
            a,i = top
            sub = arr[i-1:i+3] # 切片映射（修改 sub 会反映到 arr 上）
            if not (retained[i:i+2].all() and a == sub[1:3].sum() ): # 已经被删除过，则跳过
                H.pop()
            else: # 有效，先计算操作，再用 replace 替换，减少维护堆的成本
                # 更新 dec_times（减去变化前的局部逆序数）
                dec_times -= np.sum(sub[:3]>sub[1:],dtype=np.int32) # 更新 dec_times
                sub[1:3] = a # 合并拷贝成双份，不会破坏逆序数的计算，还能避免硬删除
                retained[i+1] = False # 软删除标记为 False，表示待删除的元素（降低复杂度）
                # 更新 dec_times（加上变化后的局部逆序数）
                dec_times += np.sum(sub[:3]>sub[1:],dtype=np.int32) # 更新 dec_times
                if dec_times <= 0:break

                # 更新堆，首先生成左右相邻的和及其索引（注意越界情况）
                new_items = [ (arr[j:j+2].sum(),j) for j in (i-1,i+1) if 0<j<n ]
                # new_items[0] 一定存在！否则 dec_times == 0 已经跳出循环
                assert new_items
                H.replace(new_items[0]) # 替换堆顶元素（比先PoP后Push更快）
                if len(new_items) > 1:
                    H.push(new_items[1]) # 如果存在
            
        return n-(retained.sum().item()-2) # 因为操作次数等价于删除的相邻对数，所以返回 n - (保留元素个数，注意arr含两个哨兵)

