#include <string>

using namespace std;

class Solution {
private:
    int dis(int pos1, int pos2){
        int x1 = pos1 / 6, y1 = pos1 % 6;
        int x2 = pos2 / 6, y2 = pos2 % 6;
        return abs(x1 - x2) + abs(y1 - y2);
    }
public:
    int minimumDistance(string word) {
        int dp[2][26]={0};
        int i_dp = 0;
        for(int c = 1; c<word.size(); ++c){
            int j=word[c-1]-'A', k = word[c]-'A';
            // 情况一：还是移动上一个手指（相当于原 dp2[i][j] + dis(j,k) -> dp2[i][k]）
            for(int i=0; i<26 ; i++){
                dp[!i_dp][i] = dp[i_dp][i] + dis(j, k);
            }
            // 情况二：移动另一个手指（则未移动到手指位置变成 j）
            for(int i=0; i<26 ; i++){
                dp[!i_dp][j] = min(dp[!i_dp][j], dp[i_dp][i] + dis(i,k));
            }
            i_dp = !i_dp;
        }
        int res = dp[i_dp][0];
        for(int i=1; i<26 ; i++){
            res = min(res, dp[i_dp][i]);
        }
        return res;
    }
};