# 调试开关
__DEBUG__ = True
from math import comb

class Solution:
    def nthSmallest(self, n: int, k: int) -> int:
        """
        k_1数：是一种二进制表达中恰好包含 k 个 1 的正整数
        返回：求第 n 小的 k_1 数
        """
        if __DEBUG__:
            print(f"n={n}, k={k}")
        if n <= 0 or k <= 0:
            return 0
        
        # 二分查找最小的 m，使得 C(m, k) >= n
        # 下界：至少需要 k 位才能有 k 个 1，所以 m >= k
        # 上界：题目保证答案 < 2^50，所以 m <= 50
        low = k      # 因为我们要找的是满足 C(m, k) >= n 的最小 m，从 k 开始
        high = 50        # 题目保证答案小于 2^50
        
        if __DEBUG__:
            print(f"  二分查找：low={low}, high={high}")
            print(f"  目标：找到最小的 m 使得 C(m, {k}) >= {n}")
        
        # 二分查找：寻找第一个满足 C(m, k) >= n 的 m
        while low < high:
            mid = (low + high) // 2
            count = comb(mid, k)
            
            if __DEBUG__:
                print(f"    mid={mid}, C({mid}, {k}) = {count}, 比较: {count} >= {n}?")
            
            if count >= n:
                high = mid
            else:
                low = mid + 1
        
        # low 是满足 C(low, k) >= n 的最小整数
        m = low

        # 计算前 m-1 位的 k_1 数个数
        if m > 0:
            y0 = comb(m - 1, k) if k <= m - 1 else 0
        else:
            y0 = 0
        
        if __DEBUG__:
            print(f"  找到 m={m}")
            print(f"  C({m}, {k}) = {comb(m, k)} >= {n}")
            print(f"  前 {m-1} 位的 k_1 数个数 y0 = {y0}")
            print(f"  剩余需要查找的数: n' = {n} - {y0} = {n - y0}")
            print(f"  最高位位置: {m-1} (对应值 2^{m-1} = {1 << (m-1)})")
        
        # 此时 y0 < n <= C(m, k)
        # 第 n 个 k_1 数在区间 [2^(m-1), 2^m) 中
        # 设置最高位的 1，然后递归处理低位
        result = (1 << (m - 1)) + self.nthSmallest(n - y0, k - 1)
        
        if __DEBUG__:
            print(f"【结束】nthSmallest(n={n}, k={k}) = {result} ({bin(result)})")
        
        return result

# 测试用例
if __name__ == "__main__" and __DEBUG__:
    obj = Solution()
    n = 4
    k = 2
    res = obj.nthSmallest(n, k)
    print(f"{res} = {bin(res)}")  # 输出: 9 = 0b1001