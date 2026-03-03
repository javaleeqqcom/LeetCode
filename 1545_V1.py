class Solution:
    def findKthBit(self, n: int, k: int) -> str:
        def f(n,i)->int:
            if 1==n:
                assert 0==i
                return 0
            else:
                assert n>1 and i>=0
                mid = (2**(n-1))-1
                if i<mid:
                    return f(n-1,i)
                elif i == mid:
                    return 1
                else:
                    return 1-f(n-1, 2*mid - i)
        return str(f(n,k-1))