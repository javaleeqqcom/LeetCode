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

def combination(n, k):
    """计算组合数 C(n, k)"""
    if k < 0 or k > n:
        return 0
    if k == 0 or k == n:
        return 1
    result = 1
    for i in range(1, min(k, n - k) + 1):
        result = result * (n - i + 1) // i
    return result

用 lru_cache 缓存函数 bruce(a, k) 的结果，以提高效率。
def bruce(a,k):
    ans = 0
    # while a>=0:
    #     if count_1(a) == k:
    #         ans +=1
    #     a -= 1
    改为递归触发 lru_cache
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
        low1 = a & (-a)  # 提取低位连续1
        high = a ^ low1  # 去掉低位连续1
        ans = combination(count(low1), k - count_1(high)) + f(high, k)
    else:
        ans = int(count_1(a) == k) + f(a - 1, k)

    ans_true = bruce(a, k)
    if ans != ans_true:
        print("f({:4d}={:>12s} ,{})={} ≠ {} Error!".format( a,bin(a),k,ans , ans_true))
    else:
        ……

    return ans

# 添加测试用例
print("Testing f(7, 2):", f(7, 2) == bruce(7, 2))
print("Testing f(4, 1):", f(4, 1) == bruce(4, 1))
print("Testing f(4, 2):", f(4, 2) == bruce(4, 2))
print("Testing f(0, 0):", f(0, 0) == bruce(0, 0))
print("Testing f(0, 1):", f(0, 1) == bruce(0, 1))
print("Testing f(15, 3):", f(15, 3) == bruce(15, 3))
print("Testing f(31, 4):", f(31, 4) == bruce(31, 4))