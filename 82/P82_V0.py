# P82_V0.py

from typing import Optional
# 不要 from tools.custom_init import ListNode！
# 假设 ListNode 已在全局可用（由 runner 注入或提前导入）

class Solution:
    def deleteDuplicates(self, head: Optional['ListNode']) -> Optional['ListNode']:
        pred = head
        assert isinstance(pred, ListNode) or pred is None
        while pred and pred.next:
            cur = pred.next
            if cur.val == pred.val:
                pred.next = cur.next
            else:
                pred = cur
        return head