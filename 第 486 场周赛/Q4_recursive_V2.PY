# 调试开关
__DEBUG__ = True

from math import comb

class Solution:
    def nthSmallest(self, n: int, k: int) -> int:
        """
        k-1数：是一种二进制表达中恰好包含 k 个 1 的正整数
        返回：求第 n 小的 k-1 数
        """
        if __DEBUG__:
            print(f"n={n}, k={k}")
        if n <= 0 or k <= 0:
            return 0
        m0 = k-1
        y0 = comb(m0, k)
        while True:
            y1 = comb(m0 + 1, k)
            if y1 >= n:
                break
            m0 += 1
            y0 = y1
        if __DEBUG__:
            print(f"m={m0}, y={y0}")
        # 此时 y0 < n <= y1，意味着第 n 个数在 [2**m0, 2**(m0+1)) 中
        return (2 ** m0) + self.nthSmallest(n - y0, k - 1)

# 测试用例
if __name__ == "__main__" and __DEBUG__:
    obj = Solution()
    n = 4
    k = 2
    res = obj.nthSmallest(n, k)
    print(f"{res} = {bin(res)}")  # 输出: 9 = 0b1001