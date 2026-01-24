
from typing import List
__DEBUG__ = False

import heapq

inf = int(10**18)

class Node:
    def __init__(self,val,next=0,pre=0) -> None:
        self.val = val
        self.next = next
        self.pre = pre
    
    # 用于 print 调试时显示节点信息
    def __str__(self):
        return "({} < {} > {})".format(
            self.pre, self.val, self.next
        )
    
def default_None(obj,val):
    return val if obj is None else obj

class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        n = len(nums) # 因为每次操作必然减少 nums 的长度，所以记录初始长度

        # 用原位双向链表存储操作后的 nums，双哨兵防止越界，用 inf 确保越界判断
        link = [Node(-inf,1,0)]+ [Node(a,i+2,i) for i,a in enumerate(nums)] + [Node(inf,n+1,n)]

        if __DEBUG__: print(",".join(map(str,link)))

        def print_link(i):
            out = []
            idx = link[0].next
            while 0 < idx <= n:
                out.append("{}{}".format("^"if idx==i else "",link[idx].val))
                idx = link[idx].next
            print("[{}]".format(",".join(out)))

        # 用小根堆维护相邻和，每次取出最小的进行合并，元素为：（相邻和，左元素link的下标即链表指针）
        H = [(nums[i]+nums[i+1] , i+1) for i in range(n-1)]
        heapq.heapify(H) # 先初始化堆，时间复杂度O(n)

        # 总相邻递减次数（在循环中更新，当为0时说明nums已经排列为升序）
        dec_times = sum(1 for i in range(n-1) if nums[i] > nums[i+1]) 
        ans = 0
        while dec_times>0 and H: # 当还有递减次数 且 堆不为空时循环    
            aj_sum,i = H[0]
            L = link[i]
            R = link[L.next]
            if aj_sum != L.val + R.val: # 元素值已经被修改过，则跳过（被删除的元素会标记为无穷大，数据确保不会累积出现相等的结果）
                heapq.heappop(H)
            else: # 确保该元素未被删除过
                if __DEBUG__: print_link(i)

                LL_val = link[L.pre].val # 用无穷作为哨兵比较递减次数
                RR_val = link[R.next].val  # 用无穷作为哨兵比较递减
                
                # 更新 dec_times（减去变化前的局部递减次数）
                dec_times -= int(LL_val > L.val) + int(L.val>R.val) + int(R.val>RR_val)

                # 更新链表，将 R.val 加到 L.val
                L_val = link[i].val = L.val + R.val
                link[i].next = R.next
                if link[R.next]: 
                    link[R.next].pre = i
                # 删除 R 节点
                R.val = inf # 用无穷表示被删除

                # 更新 dec_times（加上变化后的局部递减次数）
                dec_times += int(LL_val > L_val) + int(L_val > RR_val)

                assert L_val == L.val

                # 更新堆，首先生成左右相邻的和及其索引（注意越界情况）
                new_items = []
                if LL_val > -inf:
                    new_items.append((LL_val + L_val,L.pre)) 
                if RR_val < inf:
                    new_items.append((L_val + RR_val,i))
                if __DEBUG__:print("new_items:",new_items)

                if new_items:
                    heapq.heapreplace(H, new_items[0]) # 替换堆顶（比先PoP后Push更快）
                    if len(new_items) > 1:
                        heapq.heappush(H, new_items[1]) # 如果存在
                else:
                    H.pop()

                ans += 1
            
        if __DEBUG__: 
            print('dec_t=',dec_times )
            print_link(0)

        return ans

if __DEBUG__:
    obj = Solution()
    # nums = [3,6,4,-6,2,-4,5,-7,-3,6,3,-4]
    nums = [1,3,2,-1,2,-2,-1]
    print(obj.minimumPairRemoval(nums))