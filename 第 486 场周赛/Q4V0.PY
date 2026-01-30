你的代码狗屁不通，应当用纯二进制运算
应当用如下递归实现：

def count_1(a):# 求 a 中 1 的个数
    return a and 1 + count_1(a & (a - 1))
def count(a): # 求 a 的二进制位数
    ans = 0
    while a:
        ans += 1
        a >>= 1
    return ans

def f(a,k): #<=a的二进制非负整数表达中，恰好包含 k 个1的个数
    # 边界处理 return 0
    ans = 0
    if a%2==1:
        low1 = a & (-a) # 提取低位连续1
        high = a ^ low1 # 去掉低位连续1
        ans = (
            组合(count(low1) , k - count_1(high)) + # 相当于固定高位 high，遍历低位 low1 的所有情况
            f(high,k) # 去掉遍历过的低位 low1 递归求高位 high
        ) 
    else:
        ans = int(count_1(a) == k) + f(a-1,k) # 若 a 刚好有k个1则算1个，然后遍历 <a 的所有情况，因为 a 的最低为为0，所以 -1 后子递归函数必然走向 a%2==1的情况。
    if __DEBUG__:
        # 要打印 f(a={a的二进制},k) = {ans}
    return ans
   
# 附上一些测试样例，用于验证代码的正确性。

bin2int = lambda bits: sum(bit * (1 << i) for i, bit in enumerate(reversed(bits)))
c = count_numbers_with_k_ones( bin2int("1001111"),2 )
print(c)
