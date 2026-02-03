from tools.solution_runner import run_solution_from_file
from custom_init import ListNode, Optional

# Definition for singly-linked list.
# class ListNode:
#     def __init__(self, val=0, next=None):
#         self.val = val
#         self.next = next
class Solution:
    def deleteDuplicates(self, head: Optional[ListNode]) -> Optional[ListNode]:
        pred = head
        assert isinstance(pred,ListNode)
        while True:
            cur = pred.next
            if cur:
                assert isinstance(cur,ListNode)
                if cur.val == pred.val:
                    pred.next = cur.next
                else:
                    pred=cur
            else:
                break
        return head

# 运行评测
if __name__ == "__main__":
    run_solution_from_file(Solution, "82q1.txt")