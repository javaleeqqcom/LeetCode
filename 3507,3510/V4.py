"""
解答错误
793 / 806 个通过的测试用例

官方题解
输入
arr =
[3,4,1,1,-3,2,4,3]

添加到测试用例
输出
7
预期结果
5
"""

import numpy as np
inf = int(1e9)
class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        ori_len = len(nums) # 因为每次操作必然减少 arr 的长度，所以记录初始长度
        arr = np.array([-inf]+ nums +[inf],dtype=np.int32) # 左右增加哨兵以省略越界判断
        # 并非有序
        dec_times = np.sum(arr[1:-2]>arr[2:-1]) # 逆序数
        while dec_times>0:
            # 构造查询表，按相邻从小到大，同大按序号小者优先（注意避开哨兵）
            adj_sum = sorted(list(zip(arr[1:-2]+arr[2:-1] ,range(1,len(arr)-2) )) )
            adjusted_min_sum = inf
            
            retained = np.ones_like(arr,dtype=bool)
            # 用外部排序的思想，每次取最小的两个数进行合并，但是需要确保求和不得大于 adjusted_min_sum
            for a,j in adj_sum:
                sub = arr[j-1:j+3] # 切片映射（修改 sub 会反映到 arr 上）
                if a < adjusted_min_sum and a == sub[1:3].sum(): # 确保本次操作不受到未更新 arr 的影响
                    # 更新 dec_times（减去变化前的局部逆序数）
                    dec_times -= np.sum(sub[:3]>sub[1:],dtype=np.int32) # 更新 dec_times
                    sub[1:3] = a # 合并拷贝成双份（以便判断 dec_times 和 adjusted_min_sum）
                    # 更新 dec_times（加上变化后的局部逆序数）
                    dec_times += np.sum(sub[:3]>sub[1:],dtype=np.int32) # 更新 dec_times
                    
                    retained[j] = False # 软删除标记为 False，表示待删除的元素（降低复杂度）
                    # 重点！更新 adjusted_min_sum，确保后续的合并操作不会破坏有序性：新插入的 a 与其相邻元素的和不会小于后续 adj_sum 的元素，否则会破坏有序性。
                    adjusted_min_sum = min(adjusted_min_sum, sub[:2].sum() ,sub[2:].sum())

                else: # 下一个最小相邻元素和是未更新再 adj_sum 中的元素，需要刷新 arr
                    arr = arr[retained]
                    break # 跳出本轮 adj_sum 的循环，开始下一轮的合并操作。

        return ori_len - len(arr) + 2 # 原始长度减去保留的长度，其中 arr 包含2个哨兵

