// class Solution:
//     def findDifferentBinaryString(self, nums: List[str]) -> str:
//         S = set()
//         for num in nums:
//             S.add(int(num,base=2))
//         for x in range(2**len(nums)):
//             if x not in S:
//                 return ("{:0%db}"%(len(nums))).format(x)
//         return ""

#include<stdio.h>
#define MAX_N 16
typedef char BOOL; // 0 for false, 1 for true 
static BOOL S[(1<<MAX_N)]; // 假设numsSize <= MAX_N
char* findDifferentBinaryString(char** nums, int numsSize) {
    // S 初始化为 0
    int max_size = 1<<numsSize;
    memset(S, 0, max_size * sizeof(BOOL));
    for (int i = 0; i < numsSize; i++) {
        int x = 0;
        for (int j = 0; j < numsSize;j++){
            x <<= 1;
            if('1'==nums[i][j]){
                x += 1;
            }
        }
        S[x] = 1;
    }
    
    // 调试信息
    // printf("max_size = %d\n",max_size);

    for(int x = 0; x < max_size; x++) {
        // 调试信息
        // printf("S[%d] = %d\n",x,S[x]);
        if(0==S[x]) {
            char* result = (char*)malloc((numsSize+1)*sizeof(char));
            int y = x;
            result[numsSize] = '\0';
            for(int j=numsSize-1; j>=0; j--) {
                result[j] = '0' + (y & 1);
                y >>= 1;
            }
            return result;
        }
    }
    return NULL;
}