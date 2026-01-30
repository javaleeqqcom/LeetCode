# 调试开关
__DEBUG__ = True
from math import comb

def popcount(x):
    """计算整数 x 的二进制表示中 1 的个数（汉明重量）"""
    return x.bit_count()  # Python 3.10+ 内置函数

def binary_length(x):
    """计算整数 x 的二进制表示长度（去除前导0）"""
    return x.bit_length()  # Python 内置函数

# 使用 lru_cache 缓存 k_1_count_B 函数的结果
from functools import lru_cache
@lru_cache(maxsize=None)
def k_1_count_B(a, k):
    ans = 0
    for i in range(a + 1):
        if popcount(i) == k:
            ans += 1
    return ans

def comb_n_1_with_k_1(n,k):
    return comb(n,k) if 0< k <= n else 0

def k_1_count(up, k, verbose=False):
    """
    k-1数：是一种二进制表达中恰好包含 k 个 1 的整数
    返回：计算不超过 up 的正整数中，包含的 k-1数 的数量
    （此函数仅用于算法分析，实际实现存在效率问题）
    """
    if k < 0 or up < 0:
        return 0
    
    if up == 0:
        return 1 if k == 0 else 0
    
    # 处理奇数情况（原代码此处逻辑存在缺陷）
    if up % 2 == 1:
        # 提取高位部分和低位连续1部分
        high = up & (up + 1)  # 清除低位连续1
        low_1 = up - high     # 低位连续1
        
        # 计算组合数：从低位连续1中选择若干位为1
        ones_in_high = popcount(high)
        ans_low = comb_n_1_with_k_1(binary_length(low_1),  k - ones_in_high) 
        
        # 递归计算高位部分
        ans_high = k_1_count(high, k)
        
        # 调试：
        if verbose :
            verbose_prefix = "f({}={},{}) = COMB({},{}) + f({}={},{}) = {}".format(
                a , bin(a) ,k ,binary_length(low_1) ,k - popcount(high) , high, bin(high) , k , ans_low + ans_high
            )
        return ans_low + ans_high
    else:
        # 当前数 up 是否为 k-1 数？
        count_current = 1 if popcount(up) == k else 0
        
        # 递归计算前一个数
        count_previous = k_1_count(up - 1, k)
        return count_current + count_previous

class Solution:
    def nthSmallest(self, n: int, k: int) -> int:
        l,r=n,(1<<50) # 答案严格小于 2^50
        # 找到 f(m,k) == n 的最小 m ，由于 f(x,k) 是关于 x 单调递增（非严格），因此可用二分法
        while l<r:
            m = (l+r)//2
            y = k_1_count(m,k)
            d = y-n

            if __DEBUG__:
                print("({}<={}<={}), y={}{}{}".format(l, m , r , y , "==" if y==n else "≠" ,n))

            if d<0:
                l = m+1
            elif d>0:
                r = m-1
            else:
                break 
        # 注意！f(x,k) 有平缓区间，要找到最小的 m，因此还需继续线性搜索
        while l<r:
            y = k_1_count(l,k)

            if __DEBUG__:
                print("f({}={},{})={}{}{}".format(l, bin(l),k , y , "==" if y==n else "≠" ,n))

            if y==n:
                break
            l += 1

        return l


# 添加测试用例
if __name__ == "__main__" and __DEBUG__:
    test_cases = [(a,k)  for a in range(1,999) for k in range(1,a)]
    
    for a, k in test_cases:
        result = k_1_count(a, k) == k_1_count_B(a, k)
        if not result:
            print(f"Testing f({a}={bin(a)}, {k}): {result}")
            k_1_count(a,k,True)
            print("")

    # obj = Solution()
    # n = 4
    # k = 18
    # print(obj.nthSmallest(n,k))