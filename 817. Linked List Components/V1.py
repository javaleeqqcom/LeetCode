try:from tools.custom_init import *
except:None

class Solution:
    def numComponents(self, head: Optional[ListNode], nums: List[int]) -> int:
        # 暴力算法，将链表转换为列表，然后遍历
        S = set(nums)
        # 滑动窗口遍历组件
        ans,cur_len = 0,0
        
        while head:
            if head.val in S:
                cur_len += 1
            elif cur_len>0:
                ans += 1
                cur_len = 0
            head = head.next
        if cur_len>0:
            ans += 1
        return ans