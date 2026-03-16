try:from tools.custom_init import *
except:None
# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def numComponents(self, head: Optional[ListNode], nums: List[int]) -> int:
        # 暴力算法，将链表转换为列表，然后遍历
        S = set(nums)
        link = []
        while head:
            link.append(head.val)
            head = head.next
        # 滑动窗口遍历组件
        ans,cur_len = 0,0
        for v in link:
            if v in S:
                cur_len += 1
            elif cur_len>0:
                ans += 1
                cur_len = 0
        if cur_len>0:
            ans += 1
        return ans