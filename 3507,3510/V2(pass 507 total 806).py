import numpy as np
from typing import List

# 将 inf 替换为 'INF' 打印
def format_array(arr):
    return [int(x) if x != np.inf else 'INF' for x in arr.tolist()]

class Solution:
    def minimumPairRemoval(self, nums: List[int]) -> int:
        nums = np.array(nums, dtype=np.int32)
        ans = 0
        inf = int(1e9)
        
        step = 0
        print(f"初始数组: {nums.tolist()}")
        
        # 并非有序
        while np.any(nums[:-1] > nums[1:]):
            step += 1
            print(f"\n--- 步骤 {step} ---")
            print(f"当前数组: {format_array(nums)}")
            
            # 构造查询表：(相邻和, 索引)，按和升序，同和则按索引升序（zip + sorted 默认如此）
            adj_sum = sorted(list(zip(np.array(nums[:-1] + nums[1:]).tolist(), range(len(nums) - 1))))
            print(f"所有相邻对 (sum, index): {adj_sum}")
            
            adjusted_min_sum = inf

            merged = False
            for a, j in adj_sum:
                if a < adjusted_min_sum:
                    print(f"  选择合并索引 {j} 和 {j+1}，值 {nums[j]} + {nums[j+1]} = {a}")
                    nums[j] = a
                    nums[j + 1] = inf  # 标记删除
                    ans += 1
                    merged = True

                    # 更新 adjusted_min_sum
                    left_val = nums[j - 1] if j >= 1 else inf
                    right_val = nums[j + 2] if j + 2 < len(nums) else inf
                    adjusted_min_sum = min(adjusted_min_sum, a + left_val, a + right_val)
                    print(f"    新 adjusted_min_sum = {adjusted_min_sum} (基于左邻 {left_val}, 右邻 {right_val})")
                    
                    # 显示合并后带 inf 的数组
                    print(f"    合并后（含 inf）: {nums.tolist()}")
                else:
                    print(f"  遇到 a={a} >= adjusted_min_sum={adjusted_min_sum}，停止本轮，准备刷新数组")
                    break
            else:
                # 如果 for 循环正常结束（没 break），说明本轮处理完所有对，也需要刷新
                print("  本轮所有对处理完毕，准备刷新数组")

            # 刷新数组：移除 inf
            nums = nums[np.where(nums != inf)]
            print(f"  刷新后数组: {format_array(nums)}")

        print(f"\n最终操作次数: {ans}")
        return ans