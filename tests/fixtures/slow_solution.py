import time


class Solution:
    def work(self, should_hang: bool, value: int) -> int:
        if should_hang:
            while True:
                time.sleep(0.01)
        return value
