from typing import List, Tuple, Dict, Set, Optional, Any, Union, Callable, Iterable # 若注释掉，会报错：NameError: name 'List' is not defined
import numpy as np
class Solution:
    def isTrionic(self, nums: List[int]) -> bool:
        d = np.diff(nums)
        m = len(d)
        print(d)

        p = 0
        while d[p]>0:
            p+=1
            if p == m:
                return False
        if 0==p: return False

        q = p
        while d[q]<0:
            q+=1
            if q == m:
                return False
        if q==p:return False

        return all(d[q:]>0)