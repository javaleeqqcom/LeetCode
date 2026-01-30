'''
1200 的 Docstring
给你个整数数组 arr，其中每个元素都 不相同。

请你找到所有具有最小绝对差的元素对，并且按升序的顺序返回。

每对元素对 [a,b] 如下：

a , b 均为数组 arr 中的元素
a < b
b - a 等于 arr 中任意两个元素的最小绝对差
'''
import numpy as np
class Solution:
    def minimumAbsDifference(self, arr: List[int]) -> List[List[int]]:
        arr.sort()
        diff = np.diff(arr)
        min_diff = min(diff)
        return [[arr[i],arr[i+1]] for i in range(len(diff)) if diff[i] == min_diff]
