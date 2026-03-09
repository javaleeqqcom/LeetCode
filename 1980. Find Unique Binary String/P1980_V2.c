
char* findDifferentBinaryString(char** nums, int numsSize) {
    char* result = (char*)malloc((numsSize+1)*sizeof(char));
    result[numsSize] = '\0';
    // 借鉴实数是不可数无穷的证明思路，用康托对角线法构造一个不在 S 中的二进制数
    for(int i = 0; i < numsSize; i++) {
        // 第 i 位 取第 i 个数的第 i 位的反
        result[i] = (nums[i][i] == '0') ? '1' : '0';
    }
    return result;
}