# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, x):
#         self.val = x
#         self.next = None

class Solution:
    def detectCycle(self, head: ListNode) -> ListNode:
        p1 = p2 =head
        # 一阶段： p2 比 p1 快2倍
        while True:
            if p2 is None:return None
            p2 = p2.next
            if p2 is None:return None
            p2 = p2.next
            p1 = p1.next
            if p1 == p2:
                break

        # 二阶段：
        p = head
        while True:
            if p == p1:
                return p
            p = p.next
            p1 = p1.next