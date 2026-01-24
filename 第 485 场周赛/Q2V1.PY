from typing import List
import sys
from collections import deque
from heapq import heappop

class Solution:
    def maxCapacity(self, costs: List[int], capacity: List[int], budget: int) -> int:
        cc = list(zip(map(lambda c:-c,costs) ,capacity)) + [(0,0)]  # 添加一个哨兵元素，可以作为只选择一台机器
        cc.sort()
        # print(cc)
        res = 0
        for i,(neg_c1,cap1) in enumerate(cc):
            # print(neg_c1,cap1)
            if budget <= -neg_c1: # 超出预算，排除当前物品
                continue
            else:
                max_cap2 = 0
                for (neg_c2,cap2) in cc[:i:-1]: # 排除当前物品后，逆序遍历（预算从低到高）找容量最大的组合
                    if budget > -neg_c1 - neg_c2:
                        max_cap2 = max(max_cap2, cap1 + cap2)
                    else: # 当逆序遍历的物品总成本超过当前剩余预算，退出循环，得到最大容量
                        break
                # print(cc[:i:-1],max_cap2)
                res = max(res,max_cap2)
        return res
    
obj = Solution()
costs = [4,8,5,3];capacities = [1,5,2,7]; budget = 8
# costs = [3,5,7,4];capacities = [2,4,3,6]; budget = 7
print(obj.maxCapacity(costs, capacities, budget)) # 输出：10