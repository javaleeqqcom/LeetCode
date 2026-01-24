from typing import List

__DEBUG__ = False

import heapq

inf = int((1<<63)-1)

class Node:
    def __init__(self,val,next=0,pre=0) -> None:
        self.val = val
        self.next = next
        self.pre = pre
    
def default_None(obj,val):
    return val if obj is None else obj

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
        H = [(nums[i]+nums[i+1] , i+1) for i in range(n-1)]
        heapq.heapify(H) # 先初始化堆，时间复杂度O(n)

        # 总相邻递减次数（在循环中更新，当为0时说明nums已经排列为升序）
        dec_times = sum(1 for i in range(n-1) if nums[i] > nums[i+1]) 
        ans = 0
        while dec_times>0 and H: # 当还有递减次数 且 堆不为空时循环    
            aj_sum,i = H[0]
            L = link[i]
            R = link[L.next]
            if L.val is None or R.val is None or aj_sum != L.val + R.val: # 左右元素已经被删除过，或者元素值已经被修改过，则跳过
                heapq.heappop(H)
            else: # 确保该元素未被删除过
                LL_val = default_None(link[L.pre].val, -inf) # 用无穷作为哨兵比较递减次数
                RR_val = default_None(link[R.next].val, inf)  # 用无穷作为哨兵比较递减
                
                if __DEBUG__:
                    assert LL_val is not None
                    assert RR_val is not None
                    assert L.val is not None
                    assert R.val is not None

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
                new_items = ([] if LL_val <= -inf else [( LL_val + L_val, L.pre)]) + ([] if RR_val >= inf else [(L_val + RR_val, i)]) # 注意加括号，否则 if else 会嵌套，导致语法错误
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
    nums = [3,4,1,1,-3,2,4,3]
    print(obj.minimumPairRemoval(nums))