"""
2976 Bt V0 的 Docstring
You are given two 0-indexed strings source and target, both of length n and consisting of lowercase English letters. You are also given two 0-indexed character arrays original and changed, and an integer array cost, where cost[i] represents the cost of changing the character original[i] to the character changed[i].

You start with the string source. In one operation, you can pick a character x from the string and change it to the character y at a cost of z if there exists any index j such that cost[j] == z, original[j] == x, and changed[j] == y.

Return the minimum cost to convert the string source to the string target using any number of operations. If it is impossible to convert source to target, return -1.

Note that there may exist indices i, j such that original[j] == original[i] and changed[j] == changed[i].
"""
import numpy as np
from typing import List, Tuple
class Solution:
    def minimumCost(self, source: str, target: str, original: List[str], changed: List[str], cost: List[int]) -> int:
        # 1. 注意 len(source) == len(target) 设为 n，每个位置相互独立，可将 minimumCost(source,target,*) 其转化为 sum(minimumCost(source[i],target[i],*) for i in range(n))
        # 2. 先将 original -> (changed,cost) 构造为邻接矩阵，D[x,y]=c , x=changed[i],y=original[i],c=cost[i]。由于只有小写字母，可以用 26*26 的邻接矩阵表示。
        inf = int(10**8) # 由于 cost[i] <= 10^6 ，因此由抽屉原理可知，若可以转换，最多经过 25 次即可，因此正常的 cost 至多为 25*10^6。
        D = np.array([[inf]*26 for i in range(26)],dtype=np.int32)
        # D 的对角线为 0 
        D[1==np.eye(26,dtype=np.int32)]=0
        # 3.将字母替换为其在 D 的下标
        def f(x): return ord(x)-ord('a')
        for x,y,c in zip(original,changed,cost):
            D[f(x),f(y)] = c
        # 4. 采用 floyd 算法计算邻接矩阵的最短路径。
        for k in range(26): # 中间
            for i in range(26): # 起点
                for j in range(26): # 终点
                    D[i,j] = min(D[i,j], D[i,k] + D[k,j]) # 更新最短路径

        # print(D)
        res = 0
        for x,y in zip(source,target):
            res += D[f(x),f(y)].item()
            if res >= inf:return -1 # 注意判断 inf，提前退出
        return res
    
obj = Solution()
source = "abcd"
target = "acbe"
original = ["a","b","c","c","e","d"]
changed = ["b","c","b","e","b","e"]
cost = [2,5,5,1,2,20]
res = obj.minimumCost(source,target,original,changed,cost)
print(res)