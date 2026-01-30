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

from functools import lru_cache
# 使用 lru_cache 缓存 bruce 函数的结果
@lru_cache(maxsize=None)
def bruce(a, k):
    ans = 0
    for i in range(a + 1):
        if count_1(i) == k:
            ans += 1
    return ans

def f(a, k):
    """求 <=a 的整数的二进制表示中，恰好有 k 个1的个数"""
    if k < 0:
        return 0
    if a == 0:
        return 1 if k == 0 else 0
    
    if a < 0:
        return 0
    
    if a % 2 == 1:
        # 提取低位连续1
        # low1 = a & (-a)  错误！（补充python的错误的原因）
        high = a & (a+1) # 先去掉低位的1
        low1 = a - high  # 再做差得到低位的连续1
        # high = a ^ low1  # 去掉低位连续1

        if(count_1(a) == count(a)):
            print(bin(a),bin(low1),bin(high))

        ans = comb(count(low1), k - count_1(high)) + f(high, k)
    else:
        ans = int(count_1(a) == k) + f(a - 1, k)

    ans_true = bruce(a, k)
    if ans != ans_true:
        print("f({:4d}={:>12s} ,{})={} ≠ {} Error!".format(a, bin(a), k, ans, ans_true))
    else:
        print("f({:4d}={:>12s} ,{})={} = {} OK".format(a, bin(a), k, ans, ans_true))

    return ans

# 添加测试用例
print("Testing f(7, 2):", f(7, 2) == bruce(7, 2))
print("Testing f(4, 1):", f(4, 1) == bruce(4, 1))
print("Testing f(4, 2):", f(4, 2) == bruce(4, 2))
print("Testing f(0, 0):", f(0, 0) == bruce(0, 0))
print("Testing f(0, 1):", f(0, 1) == bruce(0, 1))
print("Testing f(15, 3):", f(15, 3) == bruce(15, 3))
print("Testing f(31, 4):", f(31, 4) == bruce(31, 4))