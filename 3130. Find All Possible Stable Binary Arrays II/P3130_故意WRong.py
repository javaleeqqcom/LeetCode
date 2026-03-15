from functools import lru_cache
MODULE = 10**9 + 7
class Solution:
    def numberOfStableArrays(self, zero: int, one: int, limit: int) -> int:
        k = limit + 1  # 不允许有连续 k 位相同，连续相同位数小于 k 方为合法情况

        @lru_cache(maxsize=None) # 记忆化递归
        def dfs(bit_len:int , same_cnt:int)->int:
            # 以 1 开头，有 same_cnt 个 1 的 bit_len 位二进制数中的合法情况数模 MODULE
            nonlocal k
            if (bit_len - same_cnt) < 0 or same_cnt <= 0:
                return 0
            if 0 == (bit_len - same_cnt):
                return int(k >= same_cnt)
            
            sub = (
                # 1. 以 11 开头的情况，注意递归只是去掉最高位的1个1（因此不是 same_cnt-2），注意其中包含第3点的非法情况数；
                + dfs((bit_len - 1), same_cnt - 1) , 
                # 2. 以 10 开头的情况，相当于递归高位为 0，same_cnt-1 个1（去掉最高位1），(bit_len - same_cnt) 个0，代入 dfs 互换参数即可；
                + dfs(bit_len - 1, (bit_len - same_cnt)) , 
                # 3. 第1点需要剔除 11...110x...xx （高位连续 k 位为 1 时，然后接着0）的情况，相当于递归高位为 0，仅剩 same_cnt-k 个1 的情况。
                - dfs(bit_len - k, (bit_len - same_cnt))   
            )

            # print(c0,same_cnt,f"sum{sub}={sum(sub)}")
            return sum(sub) % MODULE # 递归正确时 sum(sub) 不可能为负值

        return (dfs(one+zero,zero) + dfs(one+zero,one)) % MODULE
