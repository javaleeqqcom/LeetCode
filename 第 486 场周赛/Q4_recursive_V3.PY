# 调试开关
__DEBUG__ = False

class Solution:
    def __init__(self) -> None:
        """
        初始化组合数表
        使用帕斯卡三角形递推计算，避免重复计算组合数
        题目保证答案严格小于 2^50，所以最大位数不超过 50
        """
        # 预计算组合数表，最多计算到 50 行（对应 50 位二进制数）
        self._comb = [[1], [1, 1]]  # 第0行: C(0,0)=1, 第1行: C(1,0)=C(1,1)=1
        
    def comb(self, m: int, k: int) -> int:
        """
        计算组合数 C(m, k)，使用记忆化避免重复计算
        
        参数:
            m: 总数
            k: 选择数
            
        返回:
            组合数 C(m, k)
        """
        if __DEBUG__: assert 0 <= k <= m # math.comb 也是不设置边界保护的

        # 如果组合数表不够大，动态扩展
        while len(self._comb) <= m:
            n = len(self._comb)  # 当前行数
            # 计算第 n 行的组合数
            new_row = [1]  # C(n, 0) = 1
            for i in range(1, n):
                # C(n, i) = C(n-1, i-1) + C(n-1, i)
                new_row.append(self._comb[n-1][i-1] + self._comb[n-1][i])
            new_row.append(1)  # C(n, n) = 1
            self._comb.append(new_row)
        
        return self._comb[m][k]
    
    def nthSmallest(self, n: int, k: int) -> int:
        """
        k-1数：是一种二进制表达中恰好包含 k 个 1 的正整数
        返回：求第 n 小的 k-1 数
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
            count = self.comb(mid, k)
            
            if __DEBUG__:
                print(f"    mid={mid}, C({mid}, {k}) = {count}, 比较: {count} >= {n}?")
            
            if count >= n:
                high = mid
            else:
                low = mid + 1
        
        # low 是满足 C(low, k) >= n 的最小整数
        m = low

        # 计算前 m-1 位的 k-1 数个数
        if m > 0:
            y0 = self.comb(m - 1, k) if k <= m - 1 else 0
        else:
            y0 = 0
        
        if __DEBUG__:
            print(f"  找到 m={m}")
            print(f"  C({m}, {k}) = {self.comb(m, k)} >= {n}")
            print(f"  前 {m-1} 位的 k-1 数个数 y0 = {y0}")
            print(f"  剩余需要查找的数: n' = {n} - {y0} = {n - y0}")
            print(f"  最高位位置: {m-1} (对应值 2^{m-1} = {1 << (m-1)})")
        
        # 此时 y0 < n <= C(m, k)
        # 第 n 个 k-1 数在区间 [2^(m-1), 2^m) 中
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