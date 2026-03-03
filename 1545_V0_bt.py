
class Solution:

    @classmethod
    def reverse_and_flip(cls,s):
        return "".join(["0" if i=="1" else "1" for i in s[::-1]])


    def __init__(self) -> None:
        self._s = ["","0"]

    def findKthBit(self, n: int, k: int) -> str:
        if n >= len(self._s):
            for i in range(len(self._s),n+1):
                self._s.append(
                    self._s[i-1] + "1" + self.reverse_and_flip(self._s[i-1])
                )
        return self._s[n][k-1]

