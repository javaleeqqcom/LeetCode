# 调试开关
__DEBUG__ = True

from math import comb

def count_1(a):
    """求 a 中 1 的个数"""
    if a == 0:
        return 0
    return 1 + count_1(a & (a - 1))

def count(a):
    """求 a 的二进制位数"""
    if a == 0:
        return 0
    ans = 0
    while a:
        ans += 1
        a >>= 1
    return ans

def fbinary(m,k):
    """求 0<x<2^m 中 count_1(x)==k 的个数"""
    # 11...11(2进制m个1)中选k个的可能性（特别排除k=0,x=0的情况） + (100..00且k==1的情况)
    return (comb(m,k) if 0< k <= m else 0) + int(1==k) 

class Solution:
    def nthSmallest(self, n: int, k: int) -> int:
        """返回一个整数，表示其二进制表示中 恰好 包含 k 个 1 的第 n 小的正整数。"""
        if __DEBUG__:
            print(f"n={n},k={k}")
        if 0==n or 0 == k:return 0
        m0=k
        y0 = fbinary(m0,k)
        while True:
            y1 = fbinary(m0+1,k)
            if y1 > n:
                break
            m0,y0 = m0+1,y1

        if __DEBUG__:
            print(f"m={m0},y={y0}")

        # 此时 y0 <= n < y1，意味着第 n 个数在 [2**m,2**(m0+1)) 中

        # 因为 0<x<=(2**m0) 中有 y0 个 count_1(x)==k 的数，所以剔除最高位的1，只需要数低位的第 n-y0 个数，递归调用 nthSmallest(n-y0,k-1) 即可
        return (2**m0) + self.nthSmallest(n-y0,k-1)

# 添加测试用例
if __name__ == "__main__" and __DEBUG__:
    obj = Solution()
    n = 3
    k = 20
    res = obj.nthSmallest(n,k)
    print(f"{res}={bin(res)}")
