from typing import List
import heapq 

class Solution:
    def maxCapacity(self, costs: List[int], capacity: List[int], budget: int) -> int:
        # 以 capacity 为优先级，构建小根堆，同容量的优先检查高成本的（因为可以POP掉，确保后续遍历必然永远超支）：（-capacity[i], -costs[i]）
        # cost_cap = [(0,0,0)] + list( zip(
        #         sorted(list(zip(costs,capacity))),
        #         range(1,len(capacity)+1)
        #     )) # 添加一个哨兵元素，可以作为只选择一台机器。注意标记唯一idx，以避免将同一机器算双份
        cost_cap = [(0,0)] + sorted(list(zip(costs,capacity)))
        cost_cap = list((cost,cap,idx) for idx,(cost,cap) in enumerate(cost_cap) )

        # print(cost_cap)
        # 外循环 costs 从低成本到高成本遍历 cost1，如此内循环时可将超出成本的 cost2 从堆中删除
        H = list((-cap,-cos,idx) for cos,cap,idx in cost_cap[::-1])  
        heapq.heapify(H)
        # print(H)

        res = 0
        for cos1,cap1,idx1 in cost_cap:
            while H:
                ng_cap2,ng_cos2,idx2 = H[0]
                # print("{}&{}: cost: {}+{}={} , cap: {}+{}={}".format(idx1,idx2,cos1,-ng_cos2,cos1-ng_cos2,cap1,-ng_cap2,cap1-ng_cap2))
                if idx1 == idx2:
                    heapq.heappop(H)
                elif cos1 -ng_cos2 < budget:
                    res = max(res,cap1-ng_cap2)
                    break # 因为堆顶就是外循环的最大容量，无需继续内循环
                else: # 后续遍历时，堆顶永远超支，无需再比较
                    heapq.heappop(H)
        return res

obj = Solution()
# costs = [4,8,5,3];capacities = [1,5,2,7]; budget = 8
costs = [1,7,3];capacities = [7,3,5]; budget = 13
# costs = [3,5,7,4];capacities = [2,4,3,6]; budget = 7
print(obj.maxCapacity(costs, capacities, budget)) # 输出：10