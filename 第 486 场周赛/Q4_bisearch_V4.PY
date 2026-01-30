# 调试开关
__DEBUG__ = True
from math import comb

def popcount(x):
    """计算整数 x 的二进制表示中 1 的个数（汉明重量）"""
    # if a == 0:
    #     return 0
    # return 1 + popcount(a & (a - 1))
    return x.bit_count()  # Python 3.10+ 内置函数

def binary_length(x):
    """计算整数 x 的二进制表示长度（去除前导0）"""
    return x.bit_length()  # Python 内置函数

# 使用 lru_cache 缓存 k_1_count_Bt 函数的结果
from functools import lru_cache
@lru_cache(maxsize=None)
def k_1_count_Bt(up, k):
    """
    k_1数：是一种二进制表达中恰好包含 k 个 1 的正整数
    返回：计算不超过 up 的正整数中，包含的 k_1数 的数量
    """
    ans = 0
    for i in range(up + 1):
        if popcount(i) == k:
            ans += 1
    return ans

def k_1_count_in_b_bit(b,k):
    """ 计算b位二进制正整数中的 k_1数 的数量"""
    return comb(b,k) if 0< k <= b else 0 # 特别注意 0 不属于 k-1 数，因此 k==0 时输出 0

def k_1_count(up, k, verbose=False):
    """
    k_1数：是一种二进制表达中恰好包含 k 个 1 的正整数
    返回：计算不超过 up 的正整数中，包含的 k_1数 的数量
    （此函数仅用于算法分析，实际实现存在效率问题）
    """
    if k <= 0 or up <= 0: 
        return 0 # 不可能含有 k-1 数，因为要求是正整数
    
    # 处理奇数情况
    if up % 2 == 1:
        # 提取高位部分和低位连续1部分
        high = up & (up + 1)  # 清除低位连续1
        low_1 = up - high     # 低位连续1
        
        # 计算组合数：从低位连续1中选择若干位为1
        ones_in_high = popcount(high)
        ans_low = k_1_count_in_b_bit(binary_length(low_1),  k - ones_in_high) 
        
        # 递归计算高位部分
        ans_high = k_1_count(high, k)
        
        # 调试：
        if verbose :
            print( "k_1_count({}={},{}) = COMB({},{}) + k_1_count({}={},{}) = {}".format(
                a , bin(a) ,k ,binary_length(low_1) ,k - popcount(high) , high, bin(high) , k , ans_low + ans_high
            ))
        return ans_low + ans_high
    else:
        # 当前数 up 是否为 k-1 数？
        count_cur = 1 if popcount(up) == k else 0
        
        # 递归计算前一个数
        count_pre = k_1_count(up - 1, k)

        # 调试：
        if verbose :
            print( "k_1_count({}={},{}) = int({}=={}) + k_1_count({}={},{}) = {}".format(
                up , bin(up) ,k , popcount(up), k , up-1, bin(up-1) , k , count_cur + count_pre
            ))

        return count_cur + count_pre

def min_b_include_k_1(n, k):
    """求最小的b 使得 comb(b,k)>=n"""
    if k == 0:
        return 0  # C(b, 0) = 1 for all b >= 0
    if n <= 1:
        return k  # C(k, k) = 1 >= n
    
    b = k
    c = 1  # C(k, k) = 1
    while c < n:
        # 组合数递推公式: C(b+1, k) = C(b, k) * (b+1) / (b+1-k)
        c = c * (b + 1) // (b + 1 - k)
        b += 1
    return b

class Solution:
    def nthSmallest(self, n: int, k: int) -> int:
        l,r = n,(1<<min_b_include_k_1(n,k))
        if __DEBUG__:
            print("n={}, k={}, l={}, r={}".format(n,k,l,r))
        # 二分法
        while l < r:
            m = (l + r) // 2  # 算术平均（python整型无上限，不需要考虑溢出）
            y = k_1_count(m,k)

            if __DEBUG__:
                print("({}<={}<={}), y={}{}{}".format(l, m , r , y , "==" if y==n else "≠" ,n))

            if y < n:
                l = m + 1
            else:
                r = m
        return l

# 添加测试用例
if __name__ == "__main__" and __DEBUG__:
    test_cases = [(a,k)  for a in range(1,500) for k in range(1,a)]
    
    is_pass = True

    for a, k in test_cases:
        result = k_1_count(a, k) == k_1_count_Bt(a, k)
        if not result:
            print(f"Testing k_1_count({a}={bin(a)}, {k}): {result}")
            k_1_count(a,k,True)
            print("")
            is_pass = False

    if is_pass:
        obj = Solution()
        n = 4
        k = 18
        print(obj.nthSmallest(n,k))