class Solution:
    def numberOfStableArrays(self, zero: int, one: int, limit: int) -> int:
        bits = zero + one
        if bits > 16:
            return -1 # 超出暴力算法能力
        res = 0

        # 判断 arr 中每个长度超过 limit 的 子数组 都 同时 包含 0 和 1 。
        def check_sub_mask(x,limit):
            mask = 2**(limit+1) - 1
            for i in range(bits - limit):
                if (x & mask) == 0 or (x & mask) == mask:
                    return False
                mask <<= 1
            return True

        # 将二进制 arr 转为整型 x
        for x in range(2**(zero+one)):
            # 注意必须是计数 1 的个数，因为 arr 可以有前导 0，按 0 计数可能会少算
            if bin(x).count('1') == one and (
                limit >= bits or check_sub_mask(x,limit)
            ):
                res += 1
        return res
