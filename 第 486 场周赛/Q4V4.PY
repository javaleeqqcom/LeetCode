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

if __DEBUG__:
    from functools import lru_cache
    # 使用 lru_cache 缓存 bruce 函数的结果
    @lru_cache(maxsize=None)
    def bruce(a, k):
        ans = 0
        for i in range(a + 1):
            if count_1(i) == k:
                ans += 1
        return ans

def comb_n_1_with_k_1(n,k):
    return comb(n,k) if 0< k <= n else 0

def f(a, k ,verbose=False):
    """求 <=a 的整数的二进制表示中，恰好有 k 个1的个数"""
    if verbose:
        print("a={}={} ,k={}".format(a,bin(a),k))

    if k < 0 or a<0:
        return 0
    if a == 0:
        return int(0==k)
    
    verbose_prefix = None

    if a % 2 == 1:
        # 提取低位连续1
        # low1 = a & (-a) 错误！因为在Python中，-a使用补码表示，
        # 对于正整数a，-a实际上是～a + 1，这会导致a & (-a)只提取最低位的单个1，
        # 而不是整个低位连续1序列。
        high = a & (a + 1)  # 先去掉低位的连续1（a+1会将低位连续1变为0，高位加1）
        low1 = a - high     # 再做差得到低位的连续1
        
        ans1 = comb_n_1_with_k_1(count(low1), k - count_1(high))
        ans2 = f(high, k)
        ans = ans1 + ans2
        # 调试：
        if verbose :
            verbose_prefix = "f({}={},{}) = COMB({},{}) + f({}={},{}) = {}".format(
                a , bin(a) ,k ,count(low1) ,k - count_1(high) , high, bin(high) , k , ans
            )
    else:
        ans1 = int(count_1(a) == k)
        ans2 = f(a - 1, k)
        ans = ans1 + ans2
        # 调试：
        if verbose :
            verbose_prefix = "f({}={},{}) = int({}=={}) + f({}={},{}) = {}".format(
                a , bin(a) ,k ,count_1(a) ,k , a - 1,bin(a-1) , k , ans
            )

    if verbose :
        if a < 100:
            ans_true = bruce(a, k)
            if ans != ans_true:
                print("{} ≠ {} Error!".format(verbose_prefix, ans_true))
                print("bruce({}=={},{})={} ≠ {}+{}={}".format(a,bin(a),k,ans_true,ans1,ans2,ans))
                return -1
            else:
                print("{} == {} OK!".format(verbose_prefix, ans_true))
        else:
            print(verbose_prefix)

    return ans

def comb_b_k_gt_n(n, k):
    """求最小的b 使得 comb(b,k)>=n"""
    if k == 0:
        return 0  # C(b, 0) = 1 for all b >= 0
    if n <= 1:
        return k  # C(k, k) = 1 >= n
    
    b = k
    c = 1  # C(k, k) = 1
    while c < n:
        # 正确的递推公式: C(b+1, k) = C(b, k) * (b+1) / (b+1-k)
        c = c * (b + 1) // (b + 1 - k)
        b += 1
    return b

class Solution:
    def nthSmallest(self, n: int, k: int) -> int:
        l,r = n,(1<<comb_b_k_gt_n(n,k))
        if __DEBUG__:
            print("n={}, k={}, l={}, r={}".format(n,k,l,r))
        # 找到 f(m,k) == n 的最小 m ，由于 f(x,k) 是关于 x 单调递增（非严格），因此可用二分法（几何均数）
        while l < r:
            m = int((l*r)**0.5) # 向下取整
            y = f(m,k)
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
            y = f(l,k)

            if __DEBUG__:
                print("f({}={},{})={}{}{}".format(l, bin(l),k , y , "==" if y==n else "≠" ,n))

            if y==n:
                break
            l += 1

        return l


# 添加测试用例
if __name__ == "__main__" and __DEBUG__:
    # test_cases = [
    #     # (7, 2),
    #     # (9, 2),
    #     # (4, 1),
    #     (5, 1),
    #     (3, 1),
    #     (9, 1),
    #     # (4, 2),
    #     # (0, 0),
    #     # (0, 1),
    #     # (15, 3),
    #     # (31, 4)
    # ]
    # test_cases = [(a,k)  for a in range(1,10) for k in range(1,a)]
    
    # for a, k in test_cases:
    #     result = f(a, k) == bruce(a, k)
    #     if not result:
    #         print(f"Testing f({a}={bin(a)}, {k}): {result}")
    #         f(a,k,True)
    #         print("")

    obj = Solution()
    n = 3
    k = 20
    print(obj.nthSmallest(n,k))