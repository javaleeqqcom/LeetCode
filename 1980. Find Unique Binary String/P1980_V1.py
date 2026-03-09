class Solution:
    def findDifferentBinaryString(self, nums: List[str]) -> str:
        S = set()
        for num in nums:
            S.add(int(num,base=2))
        for x in range(2**len(nums)):
            if x not in S:
                return ("{:0%db}"%(len(nums))).format(x)
        return ""