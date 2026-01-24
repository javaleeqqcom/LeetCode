class Solution:
    def vowelConsonantScore(self, s: str) -> int:
        vowels = set(tuple("aeiou"))
        v = sum(1 for ch in s if ch in vowels)
        a_n = sum(1 for ch in s if ch.isalpha())
        c = a_n - v
        return int(v/c) if c>0 else 0