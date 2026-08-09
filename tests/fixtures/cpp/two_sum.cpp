class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        unordered_map<int, int> positions;
        for (int index = 0; index < static_cast<int>(nums.size()); ++index) {
            const int complement = target - nums[index];
            const auto found = positions.find(complement);
            if (found != positions.end()) {
                return {found->second, index};
            }
            positions[nums[index]] = index;
        }
        return {};
    }
};
