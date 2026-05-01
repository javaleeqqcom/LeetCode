from collections import Counter
class Solution:
    def checkStrings(self, s1: str, s2: str) -> bool:
        stat1_even = Counter(list(s1[::2]))
        stat1_odd = 
        stat2_even = 
        stat2_odd = Counter(list(s2[1::2]))
        return stat1_even == stat2_even and stat1_odd == stat2_odd